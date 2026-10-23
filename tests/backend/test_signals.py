"""Tests for signal-driven cache invalidation and prerendering on save."""

import json

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from backend.cache import songs_payload_key
from backend.models import Song
from category.models import Category
from chords.settings.base import CATEGORY_CACHE_KEY
from tenants.models import Tenant
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db

URL = reverse("chords:songs_api")


def payload_key(tenant):
    return songs_payload_key(tenant, False)


def prime_payload(client):
    client.get(URL)


def songs(client):
    return {entry["name"]: entry for entry in json.loads(client.get(URL).content)}


def test_song_save_invalidates(anon_client, song, tenant):
    """Saving a song, as the admin does, clears the payload without any explicit call."""
    prime_payload(anon_client)
    song.name = "Renamed"
    song.save()
    assert cache.get(payload_key(tenant)) is None
    assert list(songs(anon_client)) == ["Renamed"]


def test_new_song_visible_after_adding_category(anon_client, song, category):
    """A song created and linked to a category appears on the next request."""
    prime_payload(anon_client)
    Song.objects.create(name="Late Song", text="y").categories.add(category)
    assert "Late Song" in songs(anon_client)


def test_song_delete_invalidates(anon_client, song, tenant):
    """Deleting a song clears the payload of the tenants it belonged to."""
    prime_payload(anon_client)
    song.delete()
    assert cache.get(payload_key(tenant)) is None
    assert songs(anon_client) == {}


def test_removing_category_updates_cats(anon_client, song, tenant, category):
    """Removing a song from a category is visible in the next payload, which the cached one would hide."""
    other = Category.objects.create(tenant=tenant, name="Other", slug="other", generate_pdf=False)
    song.categories.add(other)
    prime_payload(anon_client)
    song.categories.remove(category)
    assert cache.get(payload_key(tenant)) is None
    assert songs(anon_client)["Test Song"]["cats"] == ["other"]


def test_clearing_categories_invalidates(anon_client, song, tenant):
    """song.categories.clear() clears the payload that contained the song."""
    prime_payload(anon_client)
    song.categories.clear()
    assert cache.get(payload_key(tenant)) is None
    assert songs(anon_client) == {}


def test_reverse_add_invalidates(anon_client, song, tenant, category):
    """category.song_set.add(song) invalidates the category's tenant."""
    prime_payload(anon_client)
    late = Song.objects.create(name="Reverse", text="r")
    category.song_set.add(late)
    assert cache.get(payload_key(tenant)) is None
    assert "Reverse" in songs(anon_client)


def test_category_rename_clears_payload_and_menu(anon_client, song, tenant, category):
    """Renaming a slug clears the payload, whose `cats` name it, and the category menu."""
    prime_payload(anon_client)
    cache.set(tenant_cache_key(tenant, CATEGORY_CACHE_KEY), ["menu"])
    category.slug = "renamed"
    category.save()
    assert cache.get(payload_key(tenant)) is None
    assert cache.get(tenant_cache_key(tenant, CATEGORY_CACHE_KEY)) is None
    assert songs(anon_client)["Test Song"]["cats"] == ["renamed"]


def test_category_delete_clears_payload_and_menu(anon_client, song, tenant, category):
    """Deleting a category clears the payload and the category menu."""
    prime_payload(anon_client)
    cache.set(tenant_cache_key(tenant, CATEGORY_CACHE_KEY), ["menu"])
    category.delete()
    assert cache.get(payload_key(tenant)) is None
    assert cache.get(tenant_cache_key(tenant, CATEGORY_CACHE_KEY)) is None


def test_category_move_clears_both_tenants(anon_client, song, tenant, category):
    """Moving a category to another tenant clears the payload and menu of the old and the new tenant."""
    other_tenant = Tenant.objects.create(hostname="other.localhost", name="Other", display_name="Other")
    prime_payload(anon_client)
    cache.set(payload_key(other_tenant), "[]")
    cache.set(tenant_cache_key(tenant, CATEGORY_CACHE_KEY), ["menu"])
    cache.set(tenant_cache_key(other_tenant, CATEGORY_CACHE_KEY), ["menu"])
    category.tenant = other_tenant
    category.save()
    assert cache.get(payload_key(tenant)) is None
    assert cache.get(payload_key(other_tenant)) is None
    assert cache.get(tenant_cache_key(tenant, CATEGORY_CACHE_KEY)) is None
    assert cache.get(tenant_cache_key(other_tenant, CATEGORY_CACHE_KEY)) is None


def test_other_tenant_untouched(anon_client, song, tenant):
    """Edits in one tenant leave another tenant's cached payload alone."""
    other_tenant = Tenant.objects.create(hostname="other.localhost", name="Other", display_name="Other")
    cache.set(payload_key(other_tenant), "[]")
    prime_payload(anon_client)
    song.save()
    assert cache.get(payload_key(other_tenant)) == "[]"


@override_settings(USE_PRERENDERED_MARKDOWN=True)
def test_save_prerenders_when_enabled(category):
    """With prerendering on, every save fills the prerendered column from the text."""
    song = Song.objects.create(name="Pre", text="{Ami}Hello")
    assert '<span class="chord">Ami</span>' in song.prerendered
    song.text = "{C}Changed"
    song.save()
    song.refresh_from_db()
    assert '<span class="chord">C</span>' in song.prerendered
    assert "Ami" not in song.prerendered


@override_settings(USE_PRERENDERED_MARKDOWN=True)
def test_update_fields_without_text_keeps_prerendered(category):
    """A save restricted to other fields does not re-render the text."""
    song = Song.objects.create(name="Pre", text="{Ami}Hello")
    song.text = "{C}Changed"
    song.save(update_fields=["name"])
    song.refresh_from_db()
    assert "Ami" in song.prerendered


def test_save_leaves_prerendered_alone_when_disabled(category):
    """With prerendering off (the default in tests) the column stays untouched."""
    assert settings.USE_PRERENDERED_MARKDOWN is False
    song = Song.objects.create(name="Pre", text="{Ami}Hello")
    assert song.prerendered is None
