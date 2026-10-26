"""Tests for the Song admin."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.urls import reverse

from backend.admin import SongAdmin
from backend.models import Song

pytestmark = pytest.mark.django_db


@pytest.fixture
def song_admin():
    """The admin of songs, outside of a site."""
    return SongAdmin(Song, AdminSite())


def test_categories_column_lists_every_category(song_admin, song, category, make_category, tenant):
    """The admin list shows all categories a song belongs to."""
    second = make_category(tenant, name="Second", slug="second")
    song.categories.add(second)

    rendered = song_admin.get_categories(song)

    assert category.name in rendered
    assert second.name in rendered


def test_categories_column_is_empty_without_categories(song_admin, make_song):
    """A song in no category renders an empty column."""
    assert song_admin.get_categories(make_song()) == ""


def test_admin_changelist_renders(superuser_client, song):
    """The song changelist is reachable for site administrators."""
    assert superuser_client.get("/admin/backend/song/").status_code == 200


def test_admin_song_form_has_none_of_the_editor_markup(superuser_client, song):
    """The admin has no tabs and no Bootstrap, so the lyrics widget leaves out the splitter and the tab panels."""
    response = superuser_client.get(reverse("admin:backend_song_change", args=[song.pk]))

    content = response.content.decode()
    assert "markdownx-editor" in content
    for editor_only in ("data-split", "tabpanel", "data-panel", "aria-labelledby"):
        assert editor_only not in content
