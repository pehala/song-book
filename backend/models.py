"""Models for backend app"""

from functools import partial

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    ManyToManyField,
    Model,
    PositiveSmallIntegerField,
    TextField,
    URLField,
    Value,
)
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from markdownx.models import MarkdownxField

from backend.cache import invalidate_songs_cache, invalidate_tenant_songs_cache, song_tenants, touch_songs
from category.models import Category
from chords.markdown import INLINE_RENDERER, song_renderer
from tenants.models import Tenant
from tenants.utils import tenant_cache_key


class Song(Model):
    """Song model"""

    name = CharField(verbose_name=_("Name"), max_length=100)
    date = DateField(auto_now_add=True, editable=False)
    updated_at = DateTimeField(auto_now=True, db_index=True)
    capo = PositiveSmallIntegerField(verbose_name=_("Capo"), db_default=Value(0))
    author = CharField(verbose_name=_("Author"), max_length=100, null=True, blank=True)
    link = URLField(verbose_name=_("Youtube Link"), null=True, blank=True)
    categories = ManyToManyField(Category, verbose_name=_("Categories"))
    archived = BooleanField(verbose_name=_("Archived"), default=False)
    text = MarkdownxField(verbose_name=_("Lyrics"))
    prerendered = TextField(null=True)

    def _get_rendered_markdown(self):
        """
        Returns rendered markdown for specific type of application.
        If USE_PRERENDERED_MARKDOWN is True, it will cache the changes indefinitely.
        If USE_DYNAMIC_PRERENDER is False, it will fail if there is no cached version ready
        """
        if not settings.USE_PRERENDERED_MARKDOWN:
            return song_renderer()(self.text)

        field = self.prerendered

        if field is None:
            if settings.USE_DYNAMIC_PRERENDER:
                return self.prerender()
            raise ValueError("No prerendered song found and USE_DYNAMIC_PRERENDER is set to false")
        return field

    def prerender(self, save: bool = True):
        """Generates prerendered html for specific type with a specific rendered"""
        html = song_renderer()(self.text)
        self.prerendered = html

        if save:
            self.save(update_fields=["prerendered"])
        return html

    @property
    def rendered_markdown(self):
        """Returns rendered markdown for web"""
        return self._get_rendered_markdown()

    @property
    def inline_markdown(self):
        """Returns rendered markdown with the chords inline, for outputs that cannot lay out ruby text (PDF)"""
        if song_renderer() is INLINE_RENDERER:
            return self.rendered_markdown
        return INLINE_RENDERER(self.text)

    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        verbose_name = _("Song")
        verbose_name_plural = _("Songs")
        ordering = ["date", "id"]


@receiver(pre_save, sender=Song)
def song_pre_save(sender, instance, update_fields, **kwargs):
    """Keeps the prerendered html in step with the text on every full save (views, admin, scripts)"""
    if settings.USE_PRERENDERED_MARKDOWN and update_fields is None:
        instance.prerender(save=False)


@receiver(post_save, sender=Song)
def song_saved(sender, instance, **kwargs):
    """A saved song changes every list it is in"""
    invalidate_songs_cache(instance)


@receiver(pre_delete, sender=Song)
def song_pre_delete(sender, instance, **kwargs):
    """Remember the tenants before the category links are gone"""
    instance.tenants_before_delete = song_tenants(instance)


@receiver(post_delete, sender=Song)
def song_deleted(sender, instance, **kwargs):
    """A deleted song changes every list it was in"""
    for tenant in getattr(instance, "tenants_before_delete", ()):
        invalidate_tenant_songs_cache(tenant)


@receiver(m2m_changed, sender=Song.categories.through)
def song_categories_changed(sender, instance, action, reverse, pk_set, **kwargs):
    """
    Category membership changed: lists of both the old and the new categories are stale.

    pre_remove/pre_clear run while the old links still exist, post_add once the new ones do,
    so the current links always name every affected tenant. A list rebuilt between the
    pre_ invalidation and the change would keep the old links, so post_remove/post_clear
    invalidate the remembered tenants again.
    """
    if action in ("post_remove", "post_clear"):
        for tenant in getattr(instance, "tenants_before_membership_change", ()):
            invalidate_tenant_songs_cache(tenant)
        return
    if action not in ("pre_remove", "pre_clear", "post_add"):
        return
    if reverse:
        tenants = {instance.tenant}
        touch_songs(instance.song_set.all() if action == "pre_clear" else Song.objects.filter(pk__in=pk_set))
    else:
        touch_songs(Song.objects.filter(pk=instance.pk))
        tenants = song_tenants(instance)
        if pk_set:
            tenants.update(Tenant.objects.filter(category__pk__in=pk_set))
    instance.tenants_before_membership_change = tenants
    for tenant in tenants:
        invalidate_tenant_songs_cache(tenant)


@receiver(pre_save, sender=Category)
def category_pre_save(sender, instance, **kwargs):
    """Remember the previous tenant so its payload and menu can be cleared too"""
    instance.previous_tenant_id = None
    if instance.pk:
        instance.previous_tenant_id = (
            Category.objects.filter(pk=instance.pk).values_list("tenant_id", flat=True).first()
        )


@receiver(post_save, sender=Category)
def category_saved(sender, instance, **kwargs):
    """A created, renamed or moved category changes the menu and the songs payload"""
    touch_songs(instance.song_set.all())
    tenants = {instance.tenant}
    previous_tenant_id = getattr(instance, "previous_tenant_id", None)
    if previous_tenant_id and previous_tenant_id != instance.tenant_id:
        tenants.add(Tenant.objects.get(pk=previous_tenant_id))
    for tenant in tenants:
        invalidate_tenant_songs_cache(tenant)
        transaction.on_commit(partial(cache.delete, tenant_cache_key(tenant, settings.CATEGORY_CACHE_KEY)))


@receiver(pre_delete, sender=Category)
def category_pre_delete(sender, instance, **kwargs):
    """The songs of a deleted category lose a slug, so they count as changed"""
    touch_songs(instance.song_set.all())


@receiver(post_delete, sender=Category)
def category_deleted(sender, instance, **kwargs):
    """A deleted category changes the menu and the songs payload"""
    invalidate_tenant_songs_cache(instance.tenant)
    transaction.on_commit(partial(cache.delete, tenant_cache_key(instance.tenant, settings.CATEGORY_CACHE_KEY)))
