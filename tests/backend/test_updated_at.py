"""Every way of changing what the reader shows of a song has to move `Song.updated_at`, or delta sync misses it."""

import json

import pytest
from django.core.management import call_command
from django.urls import reverse

from backend.models import Song
from tests.backend.test_views_crud import song_payload
from tests.category.test_views_move import MOVE_URL
from tests.test_move_views import move_payload

pytestmark = pytest.mark.django_db

LONG_AGO = "2020-01-01T00:00:00Z"


@pytest.fixture
def other(make_category, tenant):
    """A second category of the tenant."""
    return make_category(tenant, name="Other", slug="other")


@pytest.fixture
def third(make_category, tenant):
    """A third category of the tenant, without songs."""
    return make_category(tenant, name="Third", slug="third")


@pytest.fixture
def aged(song, other):
    """The song, in two categories and with its updated_at far in the past."""
    song.categories.add(other)
    Song.objects.filter(pk=song.pk).update(updated_at=LONG_AGO)
    return song


def moved(song):
    """Whether the song's updated_at in the database has left the distant past."""
    return Song.objects.get(pk=song.pk).updated_at.year > 2020


@pytest.mark.parametrize(
    ("instance", "changes"),
    [
        pytest.param("aged", {"name": "Renamed"}, id="song saved"),
        pytest.param("aged", {"archived": True}, id="song archived"),
        pytest.param("other", {"slug": "renamed"}, id="category renamed"),
    ],
)
def test_saving_marks_the_song(request, aged, instance, changes):
    """Saving a song, or a category it is in, marks the song as changed."""
    saved = request.getfixturevalue(instance)
    for name, value in changes.items():
        setattr(saved, name, value)

    saved.save()

    assert moved(aged)


def fixtures(request, names):
    """Returns the fixtures of the given names, keeping the nesting of lists."""
    if isinstance(names, list):
        return [fixtures(request, name) for name in names]
    return request.getfixturevalue(names)


@pytest.mark.parametrize(
    ("method", "arguments"),
    [
        pytest.param("add", ["third"], id="add"),
        pytest.param("remove", ["other"], id="remove"),
        pytest.param("set", [["category"]], id="set"),
        pytest.param("clear", [], id="clear"),
    ],
)
def test_changing_the_categories_of_the_song_marks_it(request, aged, method, arguments):
    """Adding, removing, replacing or clearing the categories of a song marks the song as changed."""
    getattr(aged.categories, method)(*fixtures(request, arguments))

    assert moved(aged)


@pytest.mark.parametrize(
    ("owner", "method", "arguments"),
    [
        pytest.param("third", "add", ["aged"], id="add"),
        pytest.param("other", "remove", ["aged"], id="remove"),
        pytest.param("other", "set", [[]], id="set"),
        pytest.param("other", "clear", [], id="clear"),
    ],
)
def test_changing_the_songs_of_a_category_marks_them(request, aged, owner, method, arguments):
    """Adding, removing, replacing or clearing the songs of a category from its side marks the songs as changed."""
    getattr(request.getfixturevalue(owner).song_set, method)(*fixtures(request, arguments))

    assert moved(aged)


def test_category_delete(aged, other):
    """Deleting a category marks its songs as changed."""
    other.delete()

    assert moved(aged)


@pytest.mark.parametrize("command", ["prerender", "clear_prerender"])
def test_command_marks_the_song(aged, command):
    """The commands that rewrite the html of the songs mark them as changed."""
    call_command(command)

    assert moved(aged)


def test_edit_view(aged, staff_client, category):
    """Editing a song in the edit form marks it as changed."""
    response = staff_client.post(
        reverse("backend:edit", args=[aged.pk]), song_payload(category, name="Edited", categories=[category.pk])
    )

    assert response.status_code == 302
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
