"""Tests for the markdown renderer and its custom plugins."""

import mistune
import pytest

from chords.markdown import INLINE_RENDERER, RUBY_RENDERER, load_renderer, song_renderer
from chords.plugins.inline import inline_chords
from chords.plugins.ruby import ruby_chords
from chords.plugins.spaces import spaces


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("{Ami}", '<span class="chord">Ami</span>&nbsp;', id="chord on its own"),
        pytest.param("Hello {C}world", '<span class="chord">C</span>&nbsp;', id="chord inside a line"),
        pytest.param("{C#maj7}", '<span class="chord">C#maj7</span>&nbsp;', id="chord with accidental"),
    ],
)
def test_chords_are_wrapped_in_a_span(source, expected):
    """Braces mark a chord, which renders as its own span"""
    assert expected in INLINE_RENDERER(source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("{Ami}", '<ruby><rt class="chord">Ami</rt></ruby>', id="chord on its own"),
        pytest.param("{C}stojí hrad", '<ruby>stojí<rt class="chord">C</rt></ruby> hrad', id="chord over a word"),
        pytest.param("kama{C}ráda", 'kama<ruby>ráda<rt class="chord">C</rt></ruby>', id="chord inside a word"),
        pytest.param("{G}/2/hrad", '<ruby><rt class="chord">G</rt></ruby>&nbsp;&nbsp;hrad', id="spaces end the word"),
        pytest.param("{D}**bold**", '<ruby><rt class="chord">D</rt></ruby><strong>bold</strong>', id="markup ends it"),
    ],
)
def test_chords_stand_over_the_following_word(source, expected):
    """The ruby renderer wraps each chord and the plain word after it in a ruby annotation"""
    assert expected in RUBY_RENDERER(source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("/1/", "&nbsp;", id="one space"),
        pytest.param("/3/", "&nbsp;&nbsp;&nbsp;", id="three spaces"),
        pytest.param("a/2/b", "a&nbsp;&nbsp;b", id="spaces between words"),
    ],
)
def test_slashes_expand_to_spaces(source, expected):
    """A number between slashes expands to that many spaces"""
    assert expected in INLINE_RENDERER(source)


def test_single_newline_becomes_a_line_break():
    """Lyrics keep their line breaks without needing trailing spaces"""
    assert "<br />" in INLINE_RENDERER("first line\nsecond line\n")


def test_paragraph_starting_with_punctuation_is_not_fast_tracked():
    """The fast paragraph parser only claims lines starting with a letter"""
    assert INLINE_RENDERER("# Heading\n").startswith("<h1")


def test_plain_text_is_wrapped_in_a_paragraph():
    """Ordinary lyrics end up inside a paragraph"""
    assert INLINE_RENDERER("just lyrics\n").startswith("<p>")


def test_song_renderer_follows_the_setting(settings):
    """SONG_RENDERER picks the renderer by its dotted path, chords above the text by default"""
    assert song_renderer() is RUBY_RENDERER

    settings.SONG_RENDERER = "chords.markdown.INLINE_RENDERER"

    assert song_renderer() is INLINE_RENDERER
    assert load_renderer("chords.markdown.INLINE_RENDERER") is INLINE_RENDERER


@pytest.mark.parametrize(
    "plugin",
    [
        pytest.param(inline_chords, id="inline chords"),
        pytest.param(ruby_chords, id="ruby chords"),
        pytest.param(spaces, id="spaces"),
    ],
)
def test_plugins_skip_registration_without_an_html_renderer(plugin):
    """Parsing to a token stream works without the html render functions"""
    markdown = mistune.create_markdown(renderer=None, plugins=[plugin])

    assert markdown("{Ami}/2/")
