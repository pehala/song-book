"""Tests for the Song model."""

import pytest

from backend.models import Song

pytestmark = pytest.mark.django_db


def test_str_contains_name_and_id(song):
    """Songs identify themselves by name and primary key"""
    assert str(song) == f"Test Song ({song.id})"


def test_hash_is_stable_for_the_same_song(song):
    """Hashing the same instance twice gives the same value"""
    assert hash(song) == hash(song)


def test_hash_includes_song_number_when_present(song):
    """A song numbered for a PDF hashes differently from the plain one"""
    plain = hash(song)
    song.song_number = 3
    assert hash(song) != plain


def test_prerender_stores_html(song):
    """prerender() renders the markdown and saves it by default"""
    html = song.prerender()

    song.refresh_from_db()
    assert song.prerendered == html
    assert "chord" in html


def test_prerender_without_save_leaves_database_untouched(song):
    """prerender(save=False) only fills the attribute"""
    song.prerender(save=False)

    assert song.prerendered is not None
    assert Song.objects.get(pk=song.pk).prerendered is None


def test_rendered_markdown_renders_on_the_fly_by_default(settings, song):
    """With prerendering disabled the markdown is rendered per request"""
    settings.USE_PRERENDERED_MARKDOWN = False
    song.prerendered = "stale"

    assert "stale" not in song.rendered_markdown
    assert "chord" in song.rendered_markdown


def test_rendered_markdown_uses_prerendered_field(settings, song):
    """With prerendering enabled the stored html wins"""
    settings.USE_PRERENDERED_MARKDOWN = True
    song.prerendered = "<p>stored</p>"

    assert song.rendered_markdown == "<p>stored</p>"


def test_rendered_markdown_renders_dynamically_when_missing(settings, song):
    """An empty prerendered field is filled in on access when allowed"""
    settings.USE_PRERENDERED_MARKDOWN = True
    settings.USE_DYNAMIC_PRERENDER = True

    rendered = song.rendered_markdown

    song.refresh_from_db()
    assert song.prerendered == rendered


def test_rendered_markdown_raises_without_dynamic_prerender(settings, song):
    """Refuse to render on the fly when the deployment forbids it"""
    settings.USE_PRERENDERED_MARKDOWN = True
    settings.USE_DYNAMIC_PRERENDER = False

    with pytest.raises(ValueError):
        song.rendered_markdown  # noqa: B018
