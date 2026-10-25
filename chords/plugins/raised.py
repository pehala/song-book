"""Markdown extension for chords raised above the word they stand over, for the PDF"""

from functools import cache

from django.contrib.staticfiles import finders
from fontTools.ttLib import TTFont
from mistune import InlineState

from chords.plugins import CHORD_RE
from chords.plugins.ruby import WORD_CHAR

# Font size of `.chord` in pdf.css relative to the text
CHORD_SCALE = 0.85
# Space, in em of the text, left after a chord that is wider than its word
CHORD_GAP = 0.2
# Advance of a character the font does not have, in em
MISSING_ADVANCE = 0.55
# The chord and the word it stands over, which may follow after spaces, and whether the chord is the last thing of
# its line
RAISED_CHORD_RE = CHORD_RE + rf"(?:[ \t]+(?={WORD_CHAR}))?(?P<word>{WORD_CHAR}*)(?P<last>(?=[ \t]*(?:\n|\Z)))?"


@cache
def advances(font_file: str):
    """Returns a function giving the width of a string in em of the font"""
    font = TTFont(finders.find(font_file))
    cmap, hmtx, units = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm

    def text_width(text: str) -> float:
        return sum(hmtx[cmap[ord(c)]][0] / units if ord(c) in cmap else MISSING_ADVANCE for c in text)

    return text_width


def parse_chords(inline, m, state: InlineState):
    """Parses a chord together with the word it stands over"""
    attrs = {"word": m.group("word"), "last": m.group("last") is not None}
    state.append_token({"type": "raised_chords", "raw": m.group("chords"), "attrs": attrs})
    return m.end()


def render_chords(renderer, text, word, last):
    """Renders the chord raised above its word. The chord is an inline box pulled back by a negative margin, so
    the word starts under its left edge; a chord wider than its word is followed by the missing space, so the pair
    is as wide as the wider of the two and the chord never covers its neighbours. A chord with no word that ends its
    line takes no room, so it hangs over the end of the line instead of wrapping onto a row of its own."""
    chord_advance = advances("OpenSans-Bold.ttf")(text)
    chord_width = CHORD_SCALE * chord_advance
    word_width = advances("OpenSans-Regular.ttf")(word)
    if not word and last:
        return rf'<span class="chord" style="margin-right: -{chord_advance:.3f}em">{text}</span>'
    if not word:
        return rf'<span class="chord" style="margin-right: {CHORD_GAP / CHORD_SCALE:.3f}em">{text}</span>'
    chord = rf'<span class="chord" style="margin-right: -{chord_advance:.3f}em">{text}</span>'
    if chord_width <= word_width:
        return chord + word
    return rf'{chord}<span style="padding-right: {chord_width + CHORD_GAP - word_width:.3f}em">{word}</span>'


def raised_chords(md):
    """A mistune plugin to support chords written above the text that follows them, laid out with inline boxes only.
    Syntax is the same as in `inline_chords`.

    :param md: Markdown instance
    """
    md.inline.register("raised_chords", RAISED_CHORD_RE, parse_chords, before="link")
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("raised_chords", render_chords)
