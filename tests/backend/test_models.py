"""Tests for the Song model."""

import pytest

from backend.models import Song

pytestmark = pytest.mark.django_db


def test_str_contains_name_and_id(song):
    """Songs identify themselves by name and primary key."""
    assert str(song) == f"Test Song ({song.id})"


def test_hash_is_stable_for_the_same_song(song):
    """Hashing the same song twice gives the same value."""
    assert hash(song) == hash(song)


def test_equal_songs_hash_equally(song):
    """Two instances of one row are interchangeable as set members or dict keys."""
    reloaded = Song.objects.get(pk=song.pk)

    assert reloaded == song
    assert hash(reloaded) == hash(song)


def test_hash_identifies_the_row_not_its_contents(song):
    """Editing a song in memory does not move it in a set."""
    before = hash(song)

    song.name = "Renamed"
    song.song_number = 3

    assert hash(song) == before


def test_prerender_stores_html(song):
    """prerender() renders the markdown and saves it by default."""
    html = song.prerender()

    song.refresh_from_db()
    assert song.prerendered == html
    assert "chord" in html


def test_prerender_without_save_leaves_database_untouched(song):
    """prerender(save=False) only fills the attribute."""
    song.prerender(save=False)

    assert song.prerendered is not None
    assert Song.objects.get(pk=song.pk).prerendered is None


def test_rendered_markdown_renders_on_the_fly_by_default(settings, song):
    """With prerendering disabled the markdown is rendered per request."""
    settings.USE_PRERENDERED_MARKDOWN = False
    song.prerendered = "stale"

    assert "stale" not in song.rendered_markdown
    assert "chord" in song.rendered_markdown


def test_prerender_uses_the_configured_renderer(settings, song):
    """SONG_RENDERER decides how the chords of a song are written."""
    settings.SONG_RENDERER = "chords.markdown.RUBY_RENDERER"

    assert "<ruby>" in song.prerender(save=False)

    settings.SONG_RENDERER = "chords.markdown.INLINE_RENDERER"

    assert "<ruby>" not in song.prerender(save=False)


def test_pdf_markdown_raises_the_chords_whatever_the_renderer(settings, song):
    """The PDF raises the chords above their words whatever SONG_RENDERER says."""
    settings.SONG_RENDERER = "chords.markdown.RUBY_RENDERER"
    song.text = "{Ami}Hello"

    assert "<ruby>" in song.rendered_markdown
    assert "<ruby>" not in song.pdf_markdown
    assert '<span class="chord" style="margin-right: -' in song.pdf_markdown


def test_pdf_markdown_ignores_the_prerendered_field(settings, song):
    """The stored html is written for the web, so the PDF renders the text itself."""
    settings.USE_PRERENDERED_MARKDOWN = True
    song.text = "{Ami}Hello"
    song.prerendered = "<p>stored</p>"

    assert "stored" not in song.pdf_markdown
    assert ">Ami</span>Hello" in song.pdf_markdown


def test_rendered_markdown_uses_prerendered_field(settings, song):
    """With prerendering enabled the stored html wins."""
    settings.USE_PRERENDERED_MARKDOWN = True
    song.prerendered = "<p>stored</p>"

    assert song.rendered_markdown == "<p>stored</p>"


def test_rendered_markdown_renders_dynamically_when_missing(settings, song):
    """An empty prerendered field is filled in on access when allowed."""
    settings.USE_PRERENDERED_MARKDOWN = True
    settings.USE_DYNAMIC_PRERENDER = True

    rendered = song.rendered_markdown

    song.refresh_from_db()
    assert song.prerendered == rendered


def test_rendered_markdown_raises_without_dynamic_prerender(settings, song):
    """Refuse to render on the fly when the deployment forbids it."""
    settings.USE_PRERENDERED_MARKDOWN = True
    settings.USE_DYNAMIC_PRERENDER = False

    with pytest.raises(ValueError):
        song.rendered_markdown  # noqa: B018
