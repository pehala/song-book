"""Tests for ETag-based client-side caching on the songs payload."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

URL = reverse("chords:songs_api")


def test_response_has_etag(anon_client, song):
    """ETag header is present on a successful response."""
    response = anon_client.get(URL)

    assert response.status_code == 200
    assert "ETag" in response


def test_304_on_matching_etag(anon_client, song):
    """Second request with matching If-None-Match returns 304 Not Modified."""
    etag = anon_client.get(URL)["ETag"]

    assert anon_client.get(URL, HTTP_IF_NONE_MATCH=etag).status_code == 304


def test_200_on_mismatched_etag(anon_client, song):
    """Request with a stale If-None-Match returns 200 with fresh content."""
    assert anon_client.get(URL, HTTP_IF_NONE_MATCH='"outdated-etag"').status_code == 200


def test_etag_changes_after_an_edit(anon_client, song):
    """Saving a song drops the cached payload, which changes the ETag and forces the browser to re-fetch."""
    etag_before = anon_client.get(URL)["ETag"]

    song.name = "Updated Name"
    song.save()

    assert anon_client.get(URL)["ETag"] != etag_before


def test_etag_differs_between_public_and_archived_lists(anon_client, superuser_client, song, archived_song):
    """The list with archived songs has an ETag of its own"""
    assert anon_client.get(URL)["ETag"] != superuser_client.get(URL)["ETag"]
