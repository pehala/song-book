"""Tests for the /<slug>/data category JSON endpoint and its cache behaviour."""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from backend.models import Song
from category.models import Category
from chords.settings.base import SONGS_CACHE_KEY
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db


def test_returns_200(anon_client, song):
    """Endpoint returns HTTP 200 for a valid category slug."""
    url = reverse("category:songs_data", kwargs={"slug": "test-cat"})
    response = anon_client.get(url)
    assert response.status_code == 200


def test_returns_json_content_type(anon_client, song):
    """Response Content-Type is application/json."""
    url = reverse("category:songs_data", kwargs={"slug": "test-cat"})
    response = anon_client.get(url)
    assert response["Content-Type"] == "application/json"


def test_response_contains_song_in_category(anon_client, song):
    """A song belonging to the category appears in the response."""
    url = reverse("category:songs_data", kwargs={"slug": "test-cat"})
    response = anon_client.get(url)
    data = json.loads(response.content)
    names = [s["name"] for s in data]
    assert "Test Song" in names


def test_song_not_in_category_excluded(anon_client, song, tenant):
    """A song from a different category does not appear in the response."""
    other_cat = Category.objects.create(tenant=tenant, name="Other", slug="other-cat", generate_pdf=False)
    other_song = Song.objects.create(name="Other Song", text="o")
    other_song.categories.add(other_cat)

    url = reverse("category:songs_data", kwargs={"slug": "test-cat"})
    response = anon_client.get(url)
    data = json.loads(response.content)
    names = [s["name"] for s in data]
    assert "Other Song" not in names


def test_unknown_slug_returns_404(anon_client, song):
    """A request for a non-existent category slug returns 404."""
    url = reverse("category:songs_data", kwargs={"slug": "nonexistent"})
    response = anon_client.get(url)
    assert response.status_code == 404


def test_category_cache_populated_after_request(anon_client, song, tenant):
    """Cache key for the category is populated after the first request."""
    url = reverse("category:songs_data", kwargs={"slug": "test-cat"})
    anon_client.get(url)
    key = tenant_cache_key(tenant, f"{SONGS_CACHE_KEY}_test-cat")
    assert cache.get(key) is not None
