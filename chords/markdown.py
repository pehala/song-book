"""Module containing Rendering function for converting Markdown to HTML"""

from functools import cache

import mistune
from django.conf import settings
from django.utils.module_loading import import_string

from chords.plugins.inline import inline_chords
from chords.plugins.paragraph import paragraph
from chords.plugins.ruby import ruby_chords
from chords.plugins.spaces import spaces


class CustomHTMLRenderer(mistune.HTMLRenderer):
    """Soft breaks are also breaks"""

    def softbreak(self) -> str:
        return r"<br />"


def create_renderer(chords_plugin):
    """Markdown renderer whose chords are handled by the given plugin"""
    return mistune.create_markdown(
        escape=False, plugins=[paragraph, chords_plugin, spaces], renderer=CustomHTMLRenderer(escape=False)
    )


INLINE_RENDERER = create_renderer(inline_chords)
RUBY_RENDERER = create_renderer(ruby_chords)


@cache
def load_renderer(path: str):
    """The renderer at the dotted path"""
    return import_string(path)


def song_renderer():
    """The renderer configured by SONG_RENDERER"""
    return load_renderer(settings.SONG_RENDERER)
