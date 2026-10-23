"""Tests for the Song admin."""

import pytest
from django.contrib.admin.sites import AdminSite

from backend.admin import SongAdmin
from backend.models import Song

pytestmark = pytest.mark.django_db


@pytest.fixture
def song_admin():
    return SongAdmin(Song, AdminSite())


def test_categories_column_lists_every_category(song_admin, song, category, make_category, tenant):
    """The admin list shows all categories a song belongs to"""
    second = make_category(tenant, name="Second", slug="second")
    song.categories.add(second)

    rendered = song_admin.get_categories(song)

    assert category.name in rendered
    assert second.name in rendered


def test_categories_column_is_empty_without_categories(song_admin, make_song):
    """A song in no category renders an empty column"""
    assert song_admin.get_categories(make_song()) == ""


def test_admin_changelist_renders(superuser_client, song):
    """The song changelist is reachable for site administrators"""
    assert superuser_client.get("/admin/backend/song/").status_code == 200
