"""Tests for the combined /api/songs endpoint."""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from backend.cache import songs_payload_key

pytestmark = pytest.mark.django_db

URL = reverse("chords:songs_api")


def fetch(client):
    """Returns the decoded songs list for the client."""
    return json.loads(client.get(URL).content)


def test_lists_songs_with_their_category_slugs(anon_client, category, make_category, tenant, make_song):
    """Each song carries the slugs of the categories it is in, which is all the browser needs to filter."""
    second = make_category(tenant, name="Second", slug="second")
    make_song(category, second, name="Both")
    make_song(second, name="Second only")

    songs = {entry["name"]: entry for entry in fetch(anon_client)}

    assert sorted(songs["Both"]["cats"]) == ["second", "test-cat"]
    assert songs["Second only"]["cats"] == ["second"]


def test_song_has_every_field_of_the_list(anon_client, song):
    """The list keeps its fields and gains `cats` before the text."""
    entry = fetch(anon_client)[0]

    assert list(entry) == ["id", "name", "capo", "author", "link", "archived", "number", "cats", "text"]


def test_response_is_json(anon_client, song):
    """The payload is served as application/json."""
    assert anon_client.get(URL)["Content-Type"] == "application/json"


def test_songs_are_numbered_with_archived_last(superuser_client, category, make_song):
    """Numbers count public songs first, archived ones are appended."""
    make_song(category, name="Hidden", archived=True)
    make_song(category, name="Public")

    entries = fetch(superuser_client)

    assert [(entry["name"], entry["number"]) for entry in entries] == [("Public", 1), ("Hidden", 2)]


@pytest.mark.parametrize(
    ("client_fixture", "names", "cache_control"),
    [
        pytest.param("anon_client", ["Test Song"], "no-cache", id="anonymous"),
        pytest.param("staff_client", ["Test Song"], "no-cache", id="tenant admin"),
        pytest.param("superuser_client", ["Test Song", "Archived Song"], "private, no-cache", id="superuser"),
    ],
)
@pytest.mark.usefixtures("song", "archived_song")
def test_only_superusers_get_the_archived_songs_in_a_private_list(request, client_fixture, names, cache_control):
    """Tenant admins share the public list, which revalidates but may be cached anywhere; superusers get their own."""
    response = request.getfixturevalue(client_fixture).get(URL)

    assert [entry["name"] for entry in json.loads(response.content)] == names
    assert response["Cache-Control"] == cache_control


def test_songs_of_other_tenants_are_left_out(anon_client, song, other_category, make_song):
    """Another tenant's songs and category slugs never show up."""
    make_song(other_category, name="Foreign")
    shared = make_song(other_category, name="Shared")
    shared.categories.add(song.categories.get())

    entries = {entry["name"]: entry for entry in fetch(anon_client)}

    assert "Foreign" not in entries
    assert entries["Shared"]["cats"] == ["test-cat"]


def test_each_song_is_listed_once(anon_client, category, make_category, tenant, make_song):
    """A song in several categories is not duplicated by the join."""
    make_song(category, make_category(tenant, name="Second", slug="second"))

    assert len(fetch(anon_client)) == 1


def test_variants_are_cached_separately(anon_client, superuser_client, tenant, song, archived_song):
    """The public and the archived list live under their own keys."""
    fetch(anon_client)
    fetch(superuser_client)

    assert cache.get(songs_payload_key(tenant, False)) != cache.get(songs_payload_key(tenant, True))
    assert cache.get(songs_payload_key(tenant, False)) is not None


def test_cache_is_used_before_building(anon_client, tenant, song):
    """A cached payload is served as is, without touching the songs."""
    cache.set(songs_payload_key(tenant, False), "[]")

    assert fetch(anon_client) == []
