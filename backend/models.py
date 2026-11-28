"""Models for backend app."""

from functools import partial

from cached_markdown_field.models import CachedMarkdownField
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    IntegerChoices,
    ManyToManyField,
    Model,
    PositiveSmallIntegerField,
    URLField,
    Value,
)
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from backend.cache import invalidate_songs_cache, invalidate_tenant_songs_cache, song_tenants, touch_songs
from category.models import Category
from chords.markdown import PDF_RENDERER, render_song
from tenants.models import Tenant
from tenants.utils import tenant_cache_key


class Song(Model):
    """Song model."""

    class PDFColumns(IntegerChoices):
        """Numbers of columns a song can be set in on a PDF page."""

        TWO = 2, "2"
        THREE = 3, "3"

    name = CharField(verbose_name=_("Name"), max_length=100)
    date = DateField(auto_now_add=True, editable=False)
    updated_at = DateTimeField(auto_now=True, db_index=True)
    capo = PositiveSmallIntegerField(verbose_name=_("Capo"), db_default=Value(0))
    author = CharField(verbose_name=_("Author"), max_length=100, null=True, blank=True)
    link = URLField(verbose_name=_("YouTube link"), null=True, blank=True)
    categories = ManyToManyField(Category, verbose_name=_("Categories"))
    archived = BooleanField(verbose_name=_("Archived"), default=False)
    pdf_columns = PositiveSmallIntegerField(
        verbose_name=_("PDF columns"),
        help_text=_("Columns of the song in PDFs; three fit a narrow song that overflows one page in two."),
        choices=PDFColumns,
        default=PDFColumns.TWO,
        db_default=Value(PDFColumns.TWO),
    )
    pdf_keep_verses = BooleanField(
        verbose_name=_("Keep verses together in PDFs"),
        help_text=_("A verse never splits between two columns; a song with long verses may need a second page."),
        default=False,
        db_default=Value(False),
    )
    text = CachedMarkdownField(verbose_name=_("Lyrics"), compiler=render_song, cache_field="prerendered")

    @property
    def pdf_markdown(self):
        """Returns rendered markdown with the chords stacked above their words, for PDF."""
        return PDF_RENDERER(self.text)

    def __str__(self):
        return f"{self.name} ({self.id})"

    class Meta:
        verbose_name = _("Song")
        verbose_name_plural = _("Songs")
        ordering = ["date", "id"]


@receiver(post_save, sender=Song)
def song_saved(sender, instance, **kwargs):
    """A saved song changes every list it is in."""
    invalidate_songs_cache(instance)


@receiver(pre_delete, sender=Song)
def song_pre_delete(sender, instance, **kwargs):
    """Remember the tenants before the category links are gone."""
    instance.tenants_before_delete = song_tenants(instance)


@receiver(post_delete, sender=Song)
def song_deleted(sender, instance, **kwargs):
    """A deleted song changes every list it was in."""
    for tenant in getattr(instance, "tenants_before_delete", ()):
        invalidate_tenant_songs_cache(tenant)


@receiver(m2m_changed, sender=Song.categories.through)
def song_categories_changed(sender, instance, action, reverse, pk_set, **kwargs):
    """Category membership changed: lists of both the old and the new categories are stale.

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
    """Remember the previous tenant so its payload and menu can be cleared too."""
    instance.previous_tenant_id = None
    if instance.pk:
        instance.previous_tenant_id = (
            Category.objects.filter(pk=instance.pk).values_list("tenant_id", flat=True).first()
        )


@receiver(post_save, sender=Category)
def category_saved(sender, instance, **kwargs):
    """A created, renamed or moved category changes the menu and the songs payload."""
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
    """The songs of a deleted category lose a slug, so they count as changed."""
    touch_songs(instance.song_set.all())


@receiver(post_delete, sender=Category)
def category_deleted(sender, instance, **kwargs):
    """A deleted category changes the menu and the songs payload."""
    invalidate_tenant_songs_cache(instance.tenant)
    transaction.on_commit(partial(cache.delete, tenant_cache_key(instance.tenant, settings.CATEGORY_CACHE_KEY)))
