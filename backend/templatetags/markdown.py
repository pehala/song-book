"""Markdown template tags"""
from django import template
from django.conf import settings
from django.template.defaultfilters import stringfilter
from markdown import markdown, Markdown
from markdownx.settings import (
    MARKDOWNX_MARKDOWN_EXTENSIONS,
    MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS,
)


def create_markdown(extensions):
    """Creates new Markdown instance"""
    if extensions is None:
        extensions = MARKDOWNX_MARKDOWN_EXTENSIONS

    return Markdown(extensions=extensions, extension_configs=MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS)


register = template.Library()

template_markdown = create_markdown(MARKDOWNX_MARKDOWN_EXTENSIONS)
pdf_markdown = create_markdown(settings.MARKDOWNX_PDF_MARKDOWN_EXTENSIONS)


@register.filter(is_safe=True)
@stringfilter
def show_markdown(text):
    """Converts markdown to HTML"""
    return template_markdown.convert(text)


@register.filter(is_safe=True)
@stringfilter
def show_pdf_markdown(text):
    """Markdownify for PDF"""
    return pdf_markdown.convert(text)


def markdownify(content, extensions=None):
    """Custom markdownify function for using with custom extensions"""
    return markdown(
        text=content,
        extensions=extensions,
        extension_configs=MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS,
    )
