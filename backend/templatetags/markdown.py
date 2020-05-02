"""Markdown template tags"""
from django import template
from django.conf import settings
from django.template.defaultfilters import stringfilter
from markdown import markdown
from markdownx.settings import MARKDOWNX_MARKDOWN_EXTENSIONS, MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS


register = template.Library()


@register.filter(is_safe=True)
@stringfilter
def show_markdown(text):
    """Converts markdown to HTML"""
    return markdownify(text)


@register.filter(is_safe=True)
@stringfilter
def show_pdf_markdown(text):
    """Markdownify for PDF"""
    return markdownify(text, extensions=settings.MARKDOWNX_PDF_MARKDOWN_EXTENSIONS)


def markdownify(content, extensions=None):
    """Custom markdownify function for using with custom extensions"""
    if extensions is None:
        extensions = MARKDOWNX_MARKDOWN_EXTENSIONS

    return markdown(
        text=content,
        extensions=extensions,
        extension_configs=MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS
    )
