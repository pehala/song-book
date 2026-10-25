"""Tests for the markdown renderer and its custom plugins."""

import re

import mistune
import pytest

from chords.markdown import INLINE_RENDERER, PDF_RENDERER, RUBY_RENDERER, load_renderer, song_renderer
from chords.plugins.inline import inline_chords
from chords.plugins.raised import CHORD_GAP, CHORD_SCALE, MISSING_ADVANCE, advances, raised_chords
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


def test_raised_chord_over_a_longer_word_takes_no_room():
    """A chord narrower than its word is pulled back over the word, which then sets the width of the pair"""
    html = PDF_RENDERER("{C}stojí")

    assert re.search(r'<span class="chord" style="margin-right: -\d+\.\d+em">C</span>stojí', html)
    assert "padding-right" not in html


def test_raised_chord_wider_than_its_word_is_followed_by_the_missing_room():
    """The word starts under the chord, and the room the chord needs beyond it is added after the word"""
    html = PDF_RENDERER("{Dmi7}a")

    chord_width = CHORD_SCALE * advances("OpenSans-Bold.ttf")("Dmi7")
    padding = chord_width + CHORD_GAP - advances("OpenSans-Regular.ttf")("a")
    assert f'<span style="padding-right: {padding:.3f}em">a</span>' in html
    assert f'margin-right: -{advances("OpenSans-Bold.ttf")("Dmi7"):.3f}em">Dmi7</span>' in html


def test_raised_chord_without_a_word_keeps_its_own_width():
    """A chord with no word under it, followed by more text, is followed by a small gap"""
    html = PDF_RENDERER("{Ami} {C}x")

    assert f'<span class="chord" style="margin-right: {CHORD_GAP / CHORD_SCALE:.3f}em">Ami</span> ' in html


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("sleví, {F#7}", id="end of the text"),
        pytest.param("sleví, {F#7}\nnext", id="end of a line"),
        pytest.param("sleví, {F#7}  \nnext", id="spaces before the end of a line"),
    ],
)
def test_raised_chord_ending_its_line_takes_no_room(source):
    """A chord with no word that ends its line hangs over the end instead of wrapping onto a row of its own"""
    html = PDF_RENDERER(source)

    assert f'margin-right: -{advances("OpenSans-Bold.ttf")("F#7"):.3f}em">F#7</span>' in html


def test_raised_chord_stands_over_the_word_after_spaces():
    """A chord followed by spaces stands over the next word, which takes the room the spaces had"""
    html = PDF_RENDERER("{Ami} Sáro, {Emi}   Sáro")

    assert ">Ami</span>Sáro, " in html
    assert ">Emi</span>Sáro" in html


@pytest.mark.parametrize(
    ("source", "after"),
    [
        pytest.param("{C} {G}x", "C</span> <span", id="another chord"),
        pytest.param("{C} **bold**", "C</span> <strong>", id="markup"),
        pytest.param("{C} /2/x", "C</span> &nbsp;", id="spaces"),
    ],
)
def test_raised_chord_keeps_the_spaces_when_no_word_follows(source, after):
    """Spaces after a chord are kept unless a plain word comes next"""
    assert after in PDF_RENDERER(source)


def test_width_of_a_character_missing_from_the_font_is_a_default():
    """Characters Open Sans lacks count as a fixed advance"""
    assert advances("OpenSans-Regular.ttf")("字") == MISSING_ADVANCE
    assert advances("OpenSans-Regular.ttf")("字字") == 2 * MISSING_ADVANCE


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
        pytest.param(raised_chords, id="raised chords"),
        pytest.param(spaces, id="spaces"),
    ],
)
def test_plugins_skip_registration_without_an_html_renderer(plugin):
    """Parsing to a token stream works without the html render functions"""
    markdown = mistune.create_markdown(renderer=None, plugins=[plugin])

    assert markdown("{Ami}/2/")
