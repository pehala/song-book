"""Tests for the /all/data JSON endpoint and its cache behaviour."""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from backend.models import Song
from chords.settings.base import SONGS_CACHE_KEY
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db

ALL_DATA_URL = reverse("chords:all_data")


def test_returns_200(anon_client, song):
    """Endpoint returns HTTP 200 for an anonymous request."""
    response = anon_client.get(ALL_DATA_URL)
    assert response.status_code == 200


def test_returns_json_content_type(anon_client, song):
    """Response Content-Type is application/json."""
    response = anon_client.get(ALL_DATA_URL)
    assert response["Content-Type"] == "application/json"


def test_response_is_valid_json(anon_client, song):
    """Response body is a valid JSON array."""
    response = anon_client.get(ALL_DATA_URL)
    data = json.loads(response.content)
    assert isinstance(data, list)


def test_response_contains_song(anon_client, song):
    """A published song appears in the response."""
    response = anon_client.get(ALL_DATA_URL)
    data = json.loads(response.content)
    names = [s["name"] for s in data]
    assert "Test Song" in names


def test_song_has_expected_fields(anon_client, song):
    """Each song entry exposes all required fields."""
    response = anon_client.get(ALL_DATA_URL)
    data = json.loads(response.content)
    assert data  # non-empty
    entry = data[0]
    for field in ("id", "name", "capo", "author", "link", "archived", "number", "text"):
        assert field in entry, f"Missing field: {field}"


def test_archived_song_excluded_for_anonymous(anon_client, song, archived_song):
    """Archived songs are hidden from anonymous users."""
    response = anon_client.get(ALL_DATA_URL)
    data = json.loads(response.content)
    names = [s["name"] for s in data]
    assert "Archived Song" not in names


def test_archived_song_included_for_superuser(superuser_client, song, archived_song):
    """Superusers see archived songs in the response."""
    response = superuser_client.get(ALL_DATA_URL)
    data = json.loads(response.content)
    names = [s["name"] for s in data]
    assert "Archived Song" in names


# --- Cache behaviour ---


def test_cache_empty_before_first_request(anon_client, song, tenant):
    """Cache key is absent before any request has been made."""
    key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_ALL")
    assert cache.get(key) is None


def test_cache_populated_after_first_request(anon_client, song, tenant):
    """Cache key is populated after the first request."""
    anon_client.get(ALL_DATA_URL)
    key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_ALL")
    assert cache.get(key) is not None


def test_anonymous_and_auth_cache_keys_differ(tenant):
    """Anonymous and authenticated requests use distinct cache keys."""
    anon_key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_ALL")
    auth_key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_ALL_auth")
    assert anon_key != auth_key


def test_authenticated_request_uses_separate_cache_key(staff_client, song, tenant):
    """Authenticated request populates the _auth key and leaves the anon key empty."""
    staff_client.get(ALL_DATA_URL)
    auth_key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_ALL_auth")
    anon_key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_ALL")
    assert cache.get(auth_key) is not None
    assert cache.get(anon_key) is None


def test_second_request_served_from_cache(anon_client, song, category):
    """A song added after the cache is primed does not appear in the cached response."""
    anon_client.get(ALL_DATA_URL)

    # Add a new song after caching — should not appear in cached response
    late = Song.objects.create(name="Late Song", text="y")
    late.categories.add(category)

    response = anon_client.get(ALL_DATA_URL)
    data = json.loads(response.content)
    names = [s["name"] for s in data]
    assert "Late Song" not in names
