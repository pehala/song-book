"""Tests for invalidate_songs_cache — verifies all relevant cache keys are cleared."""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from backend.cache import invalidate_songs_cache, songs_payload_key
from backend.models import Song
from backend.utils import get_git_revision, get_version

pytestmark = pytest.mark.django_db

URL = reverse("chords:songs_api")


def test_invalidate_clears_the_public_payload(anon_client, song, tenant):
    """invalidate_songs_cache deletes the cached payload of the song's tenant."""
    anon_client.get(URL)
    key = songs_payload_key(tenant, False)
    assert cache.get(key) is not None

    invalidate_songs_cache(song)
    assert cache.get(key) is None


def test_invalidate_clears_the_archived_payload(superuser_client, song, tenant):
    """invalidate_songs_cache deletes the superuser (archived-inclusive) payload."""
    superuser_client.get(URL)
    key = songs_payload_key(tenant, True)
    assert cache.get(key) is not None

    invalidate_songs_cache(song)
    assert cache.get(key) is None


def test_invalidate_leaves_other_tenants_alone(anon_client, song, other_tenant):
    """Only the tenants the song belongs to are touched."""
    key = songs_payload_key(other_tenant, False)
    cache.set(key, "[]")

    invalidate_songs_cache(song)
    assert cache.get(key) == "[]"


def test_new_song_visible_after_cache_invalidation(anon_client, song, category):
    """A newly added song is returned once the cache has been invalidated."""
    anon_client.get(URL)

    new_song = Song.objects.create(name="Brand New Song", text="z")
    new_song.categories.add(category)
    invalidate_songs_cache(new_song)

    names = [s["name"] for s in json.loads(anon_client.get(URL).content)]
    assert "Brand New Song" in names


@pytest.fixture
def clear_version_cache():
    """Both version helpers memoize their result for the whole process."""
    get_version.cache_clear()
    get_git_revision.cache_clear()
    yield
    get_version.cache_clear()
    get_git_revision.cache_clear()


@pytest.mark.usefixtures("clear_version_cache")
def test_build_settings_take_precedence_over_git(settings, monkeypatch):
    """With BUILD_DATE/BUILD_REVISION set, as in the container image, git is never run."""
    settings.BUILD_DATE = "2026/10/23"
    settings.BUILD_REVISION = "abc1234"
    monkeypatch.setattr("backend.utils.subprocess.check_output", pytest.fail)

    assert get_version() == "2026/10/23"
    assert get_git_revision() == "abc1234"
