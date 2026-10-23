"""Tests for the markdown renderer and its custom plugins."""

import mistune
import pytest

from chords.markdown import RENDERER
from chords.plugins.chords import chords
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
    assert expected in RENDERER(source)


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
    assert expected in RENDERER(source)


def test_single_newline_becomes_a_line_break():
    """Lyrics keep their line breaks without needing trailing spaces"""
    assert "<br />" in RENDERER("first line\nsecond line\n")


def test_paragraph_starting_with_punctuation_is_not_fast_tracked():
    """The fast paragraph parser only claims lines starting with a letter"""
    assert RENDERER("# Heading\n").startswith("<h1")


def test_plain_text_is_wrapped_in_a_paragraph():
    """Ordinary lyrics end up inside a paragraph"""
    assert RENDERER("just lyrics\n").startswith("<p>")


@pytest.mark.parametrize("plugin", [pytest.param(chords, id="chords"), pytest.param(spaces, id="spaces")])
def test_plugins_skip_registration_without_an_html_renderer(plugin):
    """Parsing to a token stream works without the html render functions"""
    markdown = mistune.create_markdown(renderer=None, plugins=[plugin])

    assert markdown("{Ami}/2/")
