"""Tests for the combined /api/songs endpoint."""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from backend.cache import songs_payload_key

pytestmark = pytest.mark.django_db

URL = reverse("chords:songs_api")


def fetch(client):
    return json.loads(client.get(URL).content)


def test_lists_songs_with_their_category_slugs(anon_client, category, make_category, tenant, make_song):
    """Each song carries the slugs of the categories it is in, which is all the browser needs to filter"""
    second = make_category(tenant, name="Second", slug="second")
    make_song(category, second, name="Both")
    make_song(second, name="Second only")

    songs = {entry["name"]: entry for entry in fetch(anon_client)}

    assert sorted(songs["Both"]["cats"]) == ["second", "test-cat"]
    assert songs["Second only"]["cats"] == ["second"]


def test_song_has_every_field_of_the_list(anon_client, song):
    """The list keeps its fields and gains `cats` before the text"""
    entry = fetch(anon_client)[0]

    assert list(entry) == ["id", "name", "capo", "author", "link", "archived", "number", "cats", "text"]


def test_response_is_json(anon_client, song):
    """The payload is served as application/json"""
    assert anon_client.get(URL)["Content-Type"] == "application/json"


def test_songs_are_numbered_with_archived_last(superuser_client, category, make_song):
    """Numbers count public songs first, archived ones are appended"""
    make_song(category, name="Hidden", archived=True)
    make_song(category, name="Public")

    entries = fetch(superuser_client)

    assert [(entry["name"], entry["number"]) for entry in entries] == [("Public", 1), ("Hidden", 2)]


def test_songs_of_other_tenants_are_left_out(anon_client, song, other_category, make_song):
    """Another tenant's songs and category slugs never show up"""
    make_song(other_category, name="Foreign")
    shared = make_song(other_category, name="Shared")
    shared.categories.add(song.categories.get())

    entries = {entry["name"]: entry for entry in fetch(anon_client)}

    assert "Foreign" not in entries
    assert entries["Shared"]["cats"] == ["test-cat"]


def test_each_song_is_listed_once(anon_client, category, make_category, tenant, make_song):
    """A song in several categories is not duplicated by the join"""
    make_song(category, make_category(tenant, name="Second", slug="second"))

    assert len(fetch(anon_client)) == 1


def test_archived_songs_hidden_from_anonymous(anon_client, song, archived_song):
    """Archived songs are only for superusers"""
    assert [entry["name"] for entry in fetch(anon_client)] == ["Test Song"]


def test_archived_songs_shown_to_superuser(superuser_client, song, archived_song):
    """Superusers get the archived songs as well"""
    assert {entry["name"] for entry in fetch(superuser_client)} == {"Test Song", "Archived Song"}


def test_tenant_admins_share_the_public_variant(staff_client, song, archived_song):
    """Only superusers see archived songs, tenant administrators do not"""
    assert [entry["name"] for entry in fetch(staff_client)] == ["Test Song"]


def test_public_variant_may_be_cached_by_anyone(anon_client, song):
    """The public list revalidates on every use but is not private"""
    assert anon_client.get(URL)["Cache-Control"] == "no-cache"


def test_archived_variant_is_private(superuser_client, song):
    """The list with archived songs stays out of shared caches"""
    assert superuser_client.get(URL)["Cache-Control"] == "private, no-cache"


def test_matching_etag_answers_304(anon_client, song):
    """A client holding the current list gets no body"""
    etag = anon_client.get(URL)["ETag"]

    assert anon_client.get(URL, HTTP_IF_NONE_MATCH=etag).status_code == 304


def test_variants_are_cached_separately(anon_client, superuser_client, tenant, song, archived_song):
    """The public and the archived list live under their own keys"""
    fetch(anon_client)
    fetch(superuser_client)

    assert cache.get(songs_payload_key(tenant, False)) != cache.get(songs_payload_key(tenant, True))
    assert cache.get(songs_payload_key(tenant, False)) is not None


def test_cache_is_used_before_building(anon_client, tenant, song):
    """A cached payload is served as is, without touching the songs"""
    cache.set(songs_payload_key(tenant, False), "[]")

    assert fetch(anon_client) == []


def test_editing_a_song_changes_the_payload(anon_client, tenant, song):
    """Saving a song drops the cached payload"""
    fetch(anon_client)

    song.name = "Renamed"
    song.save()

    assert cache.get(songs_payload_key(tenant, False)) is None
    assert fetch(anon_client)[0]["name"] == "Renamed"


def test_renaming_a_category_slug_changes_cats(anon_client, category, song):
    """A renamed slug is visible in the next payload"""
    fetch(anon_client)

    category.slug = "renamed"
    category.save()

    assert fetch(anon_client)[0]["cats"] == ["renamed"]


def test_moving_a_song_between_categories_changes_cats(anon_client, category, make_category, tenant, song):
    """Membership changes drop the payload too"""
    other = make_category(tenant, name="Other", slug="moved-to")
    fetch(anon_client)

    song.categories.set([other])

    assert fetch(anon_client)[0]["cats"] == ["moved-to"]
