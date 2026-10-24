"""Tests for the delta variant of /api/songs, which sends only the songs changed since the reader's copy."""

import time

import pytest
from django.urls import reverse

from backend.models import Song

pytestmark = pytest.mark.django_db

URL = reverse("chords:songs_api")


def delta(client, since=0, **headers):
    return client.get(URL, {"since": since}, **headers)


def test_delta_lists_all_ids_and_the_changed_songs(anon_client, category, make_song):
    old = make_song(category, name="Old")
    Song.objects.filter(pk=old.pk).update(updated_at="2020-01-01T00:00:00Z")
    edited = make_song(category, name="Edited")

    body = delta(anon_client, since=int(time.time()) - 5).json()

    assert body["ids"] == [old.id, edited.id]
    assert [row["id"] for row in body["changed"]] == [edited.id]
    assert body["changed"][0]["number"] == 2
    assert body["etag"] == anon_client.get(URL)["ETag"]


def test_delta_is_not_stored(anon_client, song):
    assert delta(anon_client)["Cache-Control"] == "no-store"


def test_matching_etag_still_answers_304(anon_client, song):
    etag = anon_client.get(URL)["ETag"]

    assert delta(anon_client, HTTP_IF_NONE_MATCH=etag).status_code == 304


def test_deleted_song_leaves_the_ids(anon_client, category, make_song):
    kept = make_song(category, name="Kept")
    gone = make_song(category, name="Gone")
    gone.delete()

    body = delta(anon_client, since=int(time.time()) + 100).json()

    assert body["ids"] == [kept.id]
    assert body["changed"] == []


def test_archived_songs_are_numbered_last_and_only_shown_to_superusers(
    anon_client, superuser_client, category, make_song, archived_song
):
    first = make_song(category, name="First")

    assert delta(anon_client).json()["ids"] == [first.id]
    assert delta(superuser_client).json()["ids"] == [first.id, archived_song.id]
    assert delta(superuser_client)["Cache-Control"] == "private, no-store"


def test_same_second_edit_is_included(anon_client, song):
    since = int(song.updated_at.timestamp())

    assert [row["id"] for row in delta(anon_client, since=since).json()["changed"]] == [song.id]


@pytest.mark.parametrize("since", ["", "abc", "-1", "99999999999999"])
def test_bad_since_gives_the_whole_list(anon_client, song, since):
    assert isinstance(anon_client.get(URL, {"since": since}).json(), list)


def stale(song):
    Song.objects.filter(pk=song.pk).update(updated_at="2020-01-01T00:00:00Z")


def changed_ids(client):
    return [row["id"] for row in delta(client, since=int(time.time()) - 5).json()["changed"]]


def test_category_rename_marks_its_songs(anon_client, song, category):
    stale(song)
    category.name = "Renamed"
    category.save()

    assert changed_ids(anon_client) == [song.id]


def test_category_delete_marks_its_songs(anon_client, song, category, make_category, tenant):
    other = make_category(tenant, name="Other", slug="other")
    song.categories.add(other)
    stale(song)
    category.delete()

    assert changed_ids(anon_client) == [song.id]


def test_membership_change_marks_the_song(anon_client, song, make_category, tenant):
    other = make_category(tenant, name="Other", slug="other")
    stale(song)
    song.categories.add(other)

    assert changed_ids(anon_client) == [song.id]


def test_reverse_membership_change_marks_the_songs(anon_client, song, make_category, tenant):
    other = make_category(tenant, name="Other", slug="other")
    song.categories.add(other)
    stale(song)
    other.song_set.clear()

    assert changed_ids(anon_client) == [song.id]


def test_responses_carry_their_uncompressed_size(anon_client, song):
    whole = anon_client.get(URL)
    part = delta(anon_client)

    assert int(whole["X-Songs-Size"]) == len(whole.content)
    assert int(part["X-Songs-Size"]) == len(part.content)
