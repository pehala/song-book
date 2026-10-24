"""Markdown extension for chords written above the text"""

from mistune import InlineState

from chords.plugins import CHORD_RE

# The chord and the plain word right after it, which the chord is written over
RUBY_CHORD_RE = CHORD_RE + r"(?P<word>[^\s{}<>&*_`~\[\]\\/]*)"


def parse_chords(inline, m, state: InlineState):
    """Parses a chord together with the word it stands over"""
    state.append_token({"type": "ruby_chords", "raw": m.group("chords"), "attrs": {"word": m.group("word")}})
    return m.end()


def render_chords(renderer, text, word):
    """Renders the chord as a ruby annotation over its word"""
    return rf'<ruby>{word}<rt class="chord">{text}</rt></ruby>'


def ruby_chords(md):
    """A mistune plugin to support chords written above the text that follows them.
    Syntax is the same as in `inline_chords`.

    :param md: Markdown instance
    """
    md.inline.register("ruby_chords", RUBY_CHORD_RE, parse_chords, before="link")
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("ruby_chords", render_chords)
