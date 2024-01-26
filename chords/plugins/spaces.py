"""Markdown extension for spaces"""

from mistune import InlineState

SPACES_RE = r"\/(?P<spacers>\d+)\/"


# pylint: disable=unused-argument
def parse_chords(inline, m, state: InlineState):
    """Parses tag"""
    text = m.group("spacers")
    state.append_token({"type": "spaces", "raw": text})
    return m.end()


def render_chords(renderer, text):
    """Renders tag into HTML"""
    return r"&nbsp;" * int(text)


def spaces(md):
    """A mistune plugin to insert amount of spaces.
    Inline chords are surrounded by `/`, such as /5/

    :param md: Markdown instance
    """
    md.inline.register("spaces", SPACES_RE, parse_chords, before="link")
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("spaces", render_chords)
