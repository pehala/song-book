"""Every way of changing what the reader shows of a song has to move `Song.updated_at`, or delta sync misses it."""

import json

import pytest
from django.core.management import call_command
from django.urls import reverse

from backend.models import Song
from tests.backend.test_views_crud import song_payload
from tests.category.test_views_move import MOVE_URL, move_payload

pytestmark = pytest.mark.django_db

LONG_AGO = "2020-01-01T00:00:00Z"


@pytest.fixture
def other(make_category, tenant):
    """A second category of the tenant."""
    return make_category(tenant, name="Other", slug="other")


@pytest.fixture
def aged(song, other):
    """The song, in two categories and with its updated_at far in the past."""
    song.categories.add(other)
    Song.objects.filter(pk=song.pk).update(updated_at=LONG_AGO)
    return song


def moved(song):
    """Whether the song's updated_at in the database has left the distant past."""
    return Song.objects.get(pk=song.pk).updated_at.year > 2020


def test_save(aged):
    """Saving a song marks it as changed."""
    aged.name = "Renamed"
    aged.save()

    assert moved(aged)


def test_archiving(aged):
    """Archiving a song marks it as changed."""
    aged.archived = True
    aged.save()

    assert moved(aged)


def test_edit_view(aged, staff_client, category):
    """Editing a song in the edit form marks it as changed."""
    response = staff_client.post(
        reverse("backend:edit", args=[aged.pk]), song_payload(category, name="Edited", categories=[category.pk])
    )

    assert response.status_code == 302
    assert moved(aged)


def test_forward_add(aged, make_category, tenant):
    """Adding a category to a song marks the song as changed."""
    aged.categories.add(make_category(tenant, name="Third", slug="third"))

    assert moved(aged)


def test_forward_remove(aged, other):
    """Removing a category from a song marks the song as changed."""
    aged.categories.remove(other)

    assert moved(aged)


def test_forward_set(aged, category):
    """Replacing the categories of a song marks the song as changed."""
    aged.categories.set([category])

    assert moved(aged)


def test_forward_clear(aged):
    """Clearing the categories of a song marks the song as changed."""
    aged.categories.clear()

    assert moved(aged)


def test_reverse_add(aged, make_category, tenant):
    """Adding a song to a category from the category's side marks the song as changed."""
    third = make_category(tenant, name="Third", slug="third")
    third.song_set.add(aged)

    assert moved(aged)


def test_reverse_remove(aged, other):
    """Removing a song from a category from the category's side marks the song as changed."""
    other.song_set.remove(aged)

    assert moved(aged)


def test_reverse_set(aged, other):
    """Replacing the songs of a category marks the songs it dropped as changed."""
    other.song_set.set([])

    assert moved(aged)


def test_reverse_clear(aged, other):
    """Clearing the songs of a category marks them as changed."""
    other.song_set.clear()

    assert moved(aged)


def test_category_rename(aged, other):
    """Saving a category marks its songs as changed."""
    other.slug = "renamed"
    other.save()

    assert moved(aged)


def test_category_delete(aged, other):
    """Deleting a category marks its songs as changed."""
    other.delete()

    assert moved(aged)


def test_category_move_to_another_tenant(aged, category, other_tenant, superuser_client):
    """Moving a category to another tenant marks its songs as changed."""
    response = superuser_client.post(MOVE_URL, move_payload(other_tenant, category))

    assert response.status_code == 302
    assert moved(aged)


def test_import_creates_songs_with_a_timestamp(category, tmp_path):
    """Songs created by the import command carry an updated_at."""
    source = tmp_path / "songs.json"
    source.write_text(json.dumps([{"name": "Imported", "text": "{C}one"}]), encoding="UTF-8")

    call_command("import", str(source), category=category.id)

    assert Song.objects.get(name="Imported").updated_at is not None


def test_prerender_command(aged):
    """The prerender command marks the songs it rewrites as changed."""
    call_command("prerender")

    assert moved(aged)


def test_clear_prerender_command(aged):
    """The clear_prerender command marks the songs it clears as changed."""
    call_command("clear_prerender")

    assert moved(aged)


def test_category_move_of_a_song_that_only_lives_there(song, category, other_tenant, superuser_client):
    """Such a song is not saved by the move, so only touch_songs() marks it for the new tenant's readers."""
    Song.objects.filter(pk=song.pk).update(updated_at=LONG_AGO)

    superuser_client.post(MOVE_URL, move_payload(other_tenant, category))

    assert moved(song)
