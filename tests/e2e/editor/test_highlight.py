"""Browser tests of the syntax colours of the lyrics."""

import pytest
from playwright.sync_api import expect

from tests.e2e.editor.helpers import lyrics, type_into_lyrics
from tests.e2e.test_layout import colors, contrast

CHORDS = ".token.sb-chord-name"
SPACES = ".token.sb-spaces"
SPACES_COUNT = ".token.sb-spaces-count"
STRAY_BRACES = ".token.sb-stray"


def test_chords_spaces_and_braces_without_a_chord_are_coloured(editor):
    """Each part of the syntax has a token of its own, and a brace that is no chord's is flagged."""
    lyrics(editor).fill("{Ami}Jedu takhle {C}lesem /4/ konec\n{ Ami}mezera a { sám } vnitřek\n")

    expect(editor.locator(CHORDS)).to_have_text(["Ami", "C"])
    expect(editor.locator(SPACES)).to_have_text(["/4/"])
    expect(editor.locator(SPACES_COUNT)).to_have_text(["4"])
    expect(editor.locator(STRAY_BRACES)).to_have_text(["{", "}", "{", "}"])


@pytest.mark.parametrize(
    "text",
    [
        "{Am}",
        "{ Am}",
        "{Am }",
        "{{Am}",
        "{A}{B}{C}",
        "{C/2/}",
        "{Am\n}",
        "\\{Am}",
        "`{Am}`",
        "text } {Am} text {",
    ],
)
def test_what_is_coloured_as_a_chord_is_what_the_server_renders_as_one(editor, text):
    """The colours follow the server's parser, so a chord the preview does not draw is not coloured either."""
    lyrics(editor).fill(text)

    coloured = editor.locator(CHORDS).all_text_contents()
    expect(editor.locator(".markdownx-preview rt.chord")).to_have_text(coloured)


def test_a_chord_is_coloured_as_it_is_typed(editor):
    """The brace completion and the colours work on the same text."""
    type_into_lyrics(editor, "{Am")

    expect(lyrics(editor)).to_have_value("{Am}")
    expect(editor.locator(CHORDS)).to_have_text(["Am"])


def test_the_editor_is_the_text_field_the_form_sends(editor):
    """The form, the label and the phone keyboard's settings know the editor's textarea by what the field's had."""
    box = lyrics(editor)

    expect(box).to_have_attribute("name", "text")
    expect(box).to_have_id("id_text")
    for attribute in ("autocapitalize", "autocorrect"):
        expect(box).to_have_attribute(attribute, "off")
    expect(box).to_have_attribute("spellcheck", "false")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_colours_have_enough_contrast(editor, theme):
    """Chords, the number of spaces and flagged braces meet WCAG AA (4.5:1) in both themes."""
    editor.evaluate("theme => { document.documentElement.dataset.bsTheme = theme; }", theme)
    lyrics(editor).fill("{Ami}Jedu {C}lesem /4/\n{ Ami}mezera")

    for selector in (CHORDS, SPACES_COUNT, STRAY_BRACES):
        foreground, background = colors(editor, selector)
        assert contrast(foreground, background) >= 4.5, (theme, selector, foreground, background)
