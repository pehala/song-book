"""Tenant models"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Model, CharField, ManyToManyField, BooleanField, ImageField, URLField, ForeignKey, CASCADE
from django.utils.translation import gettext_lazy as _


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
    links = ManyToManyField(Link, blank=True)
    admins = ManyToManyField(get_user_model())

    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        verbose_name = _("Tenant")
        verbose_name_plural = _("Tenants")
