"""Tests for invalidate_songs_cache — verifies all relevant cache keys are cleared."""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from backend.models import Song
from backend.utils import get_git_revision, get_version, invalidate_songs_cache, regenerate_prerender
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


def test_invalidate_clears_archived_all_key(superuser_client, song, tenant):
    """invalidate_songs_cache deletes the superuser (archived-inclusive) /all cache key."""
    superuser_client.get(ALL_DATA_URL)
    key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_ALL_archived")
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


def test_regenerate_prerender_fills_the_field(settings, song):
    """With prerendering enabled a saved song gets its html refreshed"""
    settings.USE_PRERENDERED_MARKDOWN = True

    regenerate_prerender(song)

    song.refresh_from_db()
    assert "chord" in song.prerendered


def test_regenerate_prerender_is_a_noop_when_disabled(settings, song):
    """With prerendering disabled nothing is stored"""
    settings.USE_PRERENDERED_MARKDOWN = False

    regenerate_prerender(song)

    song.refresh_from_db()
    assert song.prerendered is None


@pytest.fixture
def clear_version_cache():
    """Both version helpers memoize their result for the whole process"""
    get_version.cache_clear()
    get_git_revision.cache_clear()
    yield
    get_version.cache_clear()
    get_git_revision.cache_clear()


@pytest.mark.usefixtures("clear_version_cache")
def test_build_settings_take_precedence_over_git(settings, monkeypatch):
    """With BUILD_DATE/BUILD_REVISION set, as in the container image, git is never run"""
    settings.BUILD_DATE = "2026/10/23"
    settings.BUILD_REVISION = "abc1234"
    monkeypatch.setattr("backend.utils.subprocess.check_output", pytest.fail)

    assert get_version() == "2026/10/23"
    assert get_git_revision() == "abc1234"
