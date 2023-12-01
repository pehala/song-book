"""Module containing Rendering function for converting Markdown to HTML"""
import mistune

from chords.plugins.chords import chords
from chords.plugins.paragraph import paragraph
from chords.plugins.spaces import spaces


class CustomHTMLRenderer(mistune.HTMLRenderer):
    """Soft breaks are also breaks"""

    def softbreak(self) -> str:
        return r"<br />"


RENDERER = mistune.create_markdown(
    escape=False, plugins=[paragraph, chords, spaces], renderer=CustomHTMLRenderer(escape=False)
)
