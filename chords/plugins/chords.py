"""Markdown extension for chords"""

from mistune import InlineState

CHORD_RE = r"\{(?!\s)(?P<chords>.+?)(?!\s)\}"


# pylint: disable=unused-argument
def parse_chords(inline, m, state: InlineState):
    """Parses tag"""
    text = m.group("chords")
    state.append_token({"type": "inline_chords", "raw": text})
    return m.end()


def render_chords(renderer, text):
    """Renders tag into HTML"""
    return r'<span class="chord">' + text + r"</span>&nbsp;"


def chords(md):
    """A mistune plugin to support chords.
    Inline chords are surrounded by `{}`, such as {Ami}

    :param md: Markdown instance
    """
    md.inline.register("inline_chords", CHORD_RE, parse_chords, before="link")
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("inline_chords", render_chords)
