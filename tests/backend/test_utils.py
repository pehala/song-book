"""Tests for invalidate_songs_cache — verifies all relevant cache keys are cleared."""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from backend.models import Song
from backend.utils import invalidate_songs_cache
from chords.settings.base import SONGS_CACHE_KEY
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db

ALL_DATA_URL = reverse("chords:all_data")


def _prime_all_cache(client):
    client.get(ALL_DATA_URL)


def test_invalidate_clears_anon_all_key(anon_client, song, tenant):
    """invalidate_songs_cache deletes the anonymous /all cache key."""
    _prime_all_cache(anon_client)
    key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_ALL")
    assert cache.get(key) is not None

    invalidate_songs_cache(song)
    assert cache.get(key) is None


def test_invalidate_clears_auth_all_key(staff_client, song, tenant):
    """invalidate_songs_cache deletes the authenticated /all cache key."""
    staff_client.get(ALL_DATA_URL)
    key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_ALL_auth")
    assert cache.get(key) is not None

    invalidate_songs_cache(song)
    assert cache.get(key) is None


def test_invalidate_clears_category_slug_key(anon_client, song, tenant):
    """invalidate_songs_cache deletes the per-category cache key."""
    url = reverse("category:songs_data", kwargs={"slug": "test-cat"})
    anon_client.get(url)
    key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_test-cat")
    assert cache.get(key) is not None

    invalidate_songs_cache(song)
    assert cache.get(key) is None


def test_new_song_visible_after_cache_invalidation(anon_client, song, category):
    """A newly added song is returned once the cache has been invalidated."""
    _prime_all_cache(anon_client)

    new_song = Song.objects.create(name="Brand New Song", text="z")
    new_song.categories.add(category)
    invalidate_songs_cache(new_song)

    response = anon_client.get(ALL_DATA_URL)
    data = json.loads(response.content)
    names = [s["name"] for s in data]
    assert "Brand New Song" in names
