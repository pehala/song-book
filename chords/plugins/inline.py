"""Markdown extension for chords written inline."""

from mistune import InlineState

from chords.plugins import CHORD_RE


def parse_chords(inline, m, state: InlineState):
    """Parses tag."""
    text = m.group("chords")
    state.append_token({"type": "inline_chords", "raw": text})
    return m.end()


def render_chords(renderer, text):
    """Renders tag into HTML."""
    return r'<span class="chord">' + text + r"</span>&nbsp;"


def inline_chords(md):
    """A mistune plugin to support chords inline, in front of the text.

    Inline chords are surrounded by `{}`, such as {Ami}.

    :param md: Markdown instance
    """
    md.inline.register("inline_chords", CHORD_RE, parse_chords, before="link")
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("inline_chords", render_chords)
