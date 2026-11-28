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


def test_text_html_renders_on_the_fly_without_the_cache(settings, song):
    """With the cache off the markdown is rendered per request and the stored html is left alone."""
    settings.MARKDOWN_CACHE = False
    song.prerendered = "stale"

    assert "stale" not in song.text_html
    assert "chord" in song.text_html


def test_text_html_follows_the_configured_renderer(settings, song):
    """SONG_RENDERER decides how the chords of a song are written."""
    settings.SONG_RENDERER = "chords.markdown.RUBY_RENDERER"

    assert "<ruby>" in song.text_html

    settings.SONG_RENDERER = "chords.markdown.INLINE_RENDERER"

    assert "<ruby>" not in song.text_html


def test_pdf_markdown_raises_the_chords_whatever_the_renderer(settings, song):
    """The PDF raises the chords above their words whatever SONG_RENDERER says."""
    settings.SONG_RENDERER = "chords.markdown.RUBY_RENDERER"
    song.text = "{Ami}Hello"

    assert "<ruby>" in song.text_html
    assert "<ruby>" not in song.pdf_markdown
    assert '<span class="chord" style="margin-right: -' in song.pdf_markdown


def test_pdf_markdown_ignores_the_prerendered_field(settings, song):
    """The stored html is written for the web, so the PDF renders the text itself."""
    settings.MARKDOWN_CACHE = True
    song.text = "{Ami}Hello"
    song.prerendered = "<p>stored</p>"

    assert "stored" not in song.pdf_markdown
    assert ">Ami</span>Hello" in song.pdf_markdown


def test_text_html_uses_the_stored_html(settings, song):
    """With the cache on the stored html wins."""
    settings.MARKDOWN_CACHE = True
    song.prerendered = "<p>stored</p>"

    assert song.text_html == "<p>stored</p>"


def test_text_html_renders_and_stores_html_that_is_missing(settings, song):
    """A song without html is rendered and stored when its html is read, if the deployment allows it."""
    settings.MARKDOWN_CACHE = True
    settings.MARKDOWN_CACHE_RUNTIME = True
    Song.objects.filter(pk=song.pk).update(prerendered=None)
    song.refresh_from_db()

    html = song.text_html

    assert Song.objects.get(pk=song.pk).prerendered == html


def test_text_html_raises_without_runtime_caching(settings, song):
    """Refuse to render a song without html on the fly when the deployment forbids it."""
    settings.MARKDOWN_CACHE = True
    settings.MARKDOWN_CACHE_RUNTIME = False
    Song.objects.filter(pk=song.pk).update(prerendered=None)
    song.refresh_from_db()

    with pytest.raises(ValueError):
        song.text_html  # noqa: B018
