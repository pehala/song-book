"""Tests for ETag-based client-side caching on the songs JSON endpoints."""

import pytest
from django.urls import reverse

from backend.utils import invalidate_songs_cache

pytestmark = pytest.mark.django_db


def test_all_songs_response_has_etag(anon_client, song):
    """ETag header is present on a successful /all/data response."""
    url = reverse("chords:all_data")
    response = anon_client.get(url)
    assert response.status_code == 200
    assert "ETag" in response


def test_all_songs_304_on_matching_etag(anon_client, song):
    """Second request with matching If-None-Match returns 304 Not Modified."""
    url = reverse("chords:all_data")
    first = anon_client.get(url)
    etag = first["ETag"]
    second = anon_client.get(url, HTTP_IF_NONE_MATCH=etag)
    assert second.status_code == 304


def test_all_songs_200_on_mismatched_etag(anon_client, song):
    """Request with a stale If-None-Match returns 200 with fresh content."""
    url = reverse("chords:all_data")
    response = anon_client.get(url, HTTP_IF_NONE_MATCH='"outdated-etag"')
    assert response.status_code == 200


def test_all_songs_etag_changes_after_cache_invalidation(anon_client, song):
    """ETag changes after the cache is invalidated, forcing the browser to re-fetch."""
    url = reverse("chords:all_data")
    first = anon_client.get(url)
    etag_before = first["ETag"]

    song.name = "Updated Name"
    song.save()

    invalidate_songs_cache(song)

    second = anon_client.get(url)
    assert second["ETag"] != etag_before


def test_category_songs_response_has_etag(anon_client, song):
    """ETag header is present on a successful /<slug>/data response."""
    url = reverse("category:songs_data", kwargs={"slug": "test-cat"})
    response = anon_client.get(url)
    assert response.status_code == 200
    assert "ETag" in response


def test_category_songs_304_on_matching_etag(anon_client, song):
    """Second request with matching If-None-Match returns 304 Not Modified for category endpoint."""
    url = reverse("category:songs_data", kwargs={"slug": "test-cat"})
    first = anon_client.get(url)
    etag = first["ETag"]
    second = anon_client.get(url, HTTP_IF_NONE_MATCH=etag)
    assert second.status_code == 304


def test_category_songs_200_on_mismatched_etag(anon_client, song):
    """Request with a stale If-None-Match returns 200 with fresh content for category endpoint."""
    url = reverse("category:songs_data", kwargs={"slug": "test-cat"})
    response = anon_client.get(url, HTTP_IF_NONE_MATCH='"outdated-etag"')
    assert response.status_code == 200


def test_response_has_cache_control_no_cache(anon_client, song):
    """Cache-Control: no-cache is set so browsers always revalidate with the server."""
    url = reverse("chords:all_data")
    response = anon_client.get(url)
    assert response["Cache-Control"] == "no-cache"
