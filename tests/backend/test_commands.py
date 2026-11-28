"""Tests for the backend management commands."""

import json

import pytest
from django.core.management import call_command

from backend.models import Song
from category.models import Category

pytestmark = pytest.mark.django_db


def test_prerender_fills_every_song(song, archived_song):
    """The prerender command renders markdown for all songs at once."""
    call_command("prerender")

    assert Song.objects.filter(prerendered__isnull=True).count() == 0
    assert "chord" in Song.objects.get(pk=song.pk).prerendered


def test_prerender_leaves_songs_with_current_html_alone(song):
    """Readers only download the songs whose html differs."""
    call_command("prerender")
    Song.objects.filter(pk=song.pk).update(updated_at="2020-01-01T00:00:00Z")

    call_command("prerender")

    assert Song.objects.get(pk=song.pk).updated_at.year == 2020


def test_prerender_stores_nothing_when_it_fails(song, monkeypatch):
    """A run that cannot mark the songs as changed keeps their html as it was, so the next run finds them again."""
    Song.objects.filter(pk=song.pk).update(prerendered="stale")

    def fail(songs):
        raise RuntimeError("interrupted")

    monkeypatch.setattr("backend.management.commands.prerender.touch_songs", fail)

    with pytest.raises(RuntimeError):
        call_command("prerender")

    assert Song.objects.get(pk=song.pk).prerendered == "stale"


def test_clear_prerender_empties_every_song(song):
    """The clear_prerender command drops all cached html."""
    call_command("prerender")

    call_command("clear_prerender")

    assert Song.objects.filter(prerendered__isnull=False).count() == 0


def test_import_adds_songs_to_category(category, tmp_path):
    """Songs from a JSON file are imported into the requested category."""
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
    """Importing into a category that does not exist fails loudly."""
    source = tmp_path / "songs.json"
    source.write_text("[]", encoding="UTF-8")

    with pytest.raises(Category.DoesNotExist):
        call_command("import", str(source), category=999999)


def test_import_renders_when_the_cache_is_on(settings, category, tmp_path):
    """With the cache on, imported songs arrive with their html already rendered."""
    settings.MARKDOWN_CACHE = True
    source = tmp_path / "songs.json"
    source.write_text(json.dumps([{"name": "Imported", "text": "{C}one"}]), encoding="UTF-8")

    call_command("import", str(source), category=category.id)

    assert '<rt class="chord">C</rt>' in Song.objects.get(name="Imported").prerendered
