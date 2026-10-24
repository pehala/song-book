"""Tenant models"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import BooleanField, CharField, ImageField, ManyToManyField, Model, URLField
from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from tenants.utils import tenant_cache_key


def only_png(value):
    """Raises validation error if the file is not a PNG image"""
    if not value.url and value.file.content_type != "image/png":
        raise ValidationError(_("Only PNG images are allowed"))


class Link(Model):
    """Represents a Link to other site"""

    link = URLField(verbose_name=_("Link URL"))
    display_name = CharField(verbose_name=_("Display Name"), null=True, blank=True, max_length=64)

    def __str__(self):
        return f"{self.display_name} ({self.link})"

    class Meta:
        verbose_name = _("Link")
        verbose_name_plural = _("Links")


class Tenant(Model):
    """Represents a Tenant, who has own Categories and is determined by a Host Header"""

    hostname = CharField(
        verbose_name=_("Hostname"), help_text=_("The exact hostname for this Tenant"), unique=True, max_length=64
    )
    name = CharField(verbose_name=_("Name"), help_text=_("Internal name for this Tenant"), max_length=32)
    display_name = CharField(verbose_name=_("Title"), help_text=_("Title on the Main site"), max_length=32)
    index_redirect = CharField(
        verbose_name=_("Index redirect path"),
        help_text=_("Where should new tenant redirect from index page, usually a category slug"),
        max_length=32,
    )
    all_songs_category = BooleanField(
        default=True,
        verbose_name=_("All Songs"),
        help_text=_("True, if all songs category should be added to navigation"),
    )
    icon = ImageField(
        verbose_name=_("Logo"),
        help_text=_("Optional Site logo, should be around 50x50 and in PNG format"),
        null=True,
        blank=True,
        upload_to="uploads/",
        validators=[only_png],
    )
    links = ManyToManyField(Link, blank=True, verbose_name=_("See also"))
    admins = ManyToManyField(get_user_model(), verbose_name=_("Admins"))

    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        verbose_name = _("Tenant")
        verbose_name_plural = _("Tenants")


def clear_links_menu(tenants):
    """Deletes the cached links menu of the given tenants"""
    cache.delete_many([tenant_cache_key(tenant, settings.LINKS_CACHE_KEY) for tenant in tenants])


# pylint: disable=unused-argument
@receiver(m2m_changed, sender=Tenant.links.through)
def invalidate_links_menu_on_assignment(sender, instance, action, reverse, pk_set, **kwargs):
    """Drops the cached links menu of every tenant whose links changed"""
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if not reverse:
        clear_links_menu([instance])
    elif pk_set:
        clear_links_menu(Tenant.objects.filter(pk__in=pk_set))
    else:
        clear_links_menu(Tenant.objects.all())


# pylint: disable=unused-argument
@receiver(post_save, sender=Link)
@receiver(pre_delete, sender=Link)
def invalidate_links_menu_on_edit(sender, instance, **kwargs):
    """Drops the cached links menu of the tenants using the edited link"""
    clear_links_menu(Tenant.objects.filter(links=instance))


# pylint: disable=unused-argument
@receiver(post_save, sender=Tenant)
def invalidate_categories_menu(sender, instance, **kwargs):
    """Drops the cached categories menu, which depends on the tenant's `all_songs_category`"""
    cache.delete(tenant_cache_key(instance, settings.CATEGORY_CACHE_KEY))
