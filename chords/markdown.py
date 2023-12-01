"""Module containing Rendering function for converting Markdown to HTML"""
from django.conf import settings
from markdown import Markdown


def create_markdown(extensions=None):
    """Creates new Markdown instance"""
    if extensions is None:
        extensions = settings.MARKDOWNX_MARKDOWN_EXTENSIONS

    return Markdown(extensions=extensions, extension_configs={})


RENDERER = create_markdown().convert
