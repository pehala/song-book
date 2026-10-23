"""Tests for the backend management commands."""

import json

import pytest
from django.core.management import call_command

from backend.models import Song

pytestmark = pytest.mark.django_db


def test_prerender_fills_every_song(song, archived_song):
    """The prerender command renders markdown for all songs at once"""
    call_command("prerender")

    assert Song.objects.filter(prerendered__isnull=True).count() == 0
    assert "chord" in Song.objects.get(pk=song.pk).prerendered


def test_clear_prerender_empties_every_song(song):
    """The clear_prerender command drops all cached html"""
    call_command("prerender")

    call_command("clear_prerender")

    assert Song.objects.filter(prerendered__isnull=False).count() == 0


def test_import_adds_songs_to_category(category, tmp_path):
    """Songs from a JSON file are imported into the requested category"""
    source = tmp_path / "songs.json"
    source.write_text(
        json.dumps(
            [
                {"name": "Imported One", "text": "{C}one"},
                {"name": "Imported Two", "text": "{D}two"},
            ]
        ),
        encoding="UTF-8",
    )

    call_command("import", str(source), category=category.id)

    imported = Song.objects.filter(name__startswith="Imported")
    assert imported.count() == 2
    for song in imported:
        assert list(song.categories.all()) == [category]


def test_import_rejects_unknown_category(tmp_path, db):
    """Importing into a category that does not exist fails loudly"""
    source = tmp_path / "songs.json"
    source.write_text("[]", encoding="UTF-8")

    with pytest.raises(Exception):
        call_command("import", str(source), category=999999)
