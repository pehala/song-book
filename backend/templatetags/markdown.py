from django import template
from django.template.defaultfilters import stringfilter
from markdown import markdown
from markdownx.settings import MARKDOWNX_MARKDOWN_EXTENSIONS, MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS
from markdownx.utils import markdownify
from django.conf import settings


register = template.Library()


@register.filter(is_safe=True)
@stringfilter
def show_markdown(text):
    return markdownify(text)


@register.filter(is_safe=True)
@stringfilter
def show_pdf_markdown(text):
    return markdownify(text, extensions=settings.MARKDOWNX_PDF_MARKDOWN_EXTENSIONS)


def markdownify(content, extensions=None):
    if extensions is None:
        extensions = MARKDOWNX_MARKDOWN_EXTENSIONS

    md = markdown(
        text=content,
        extensions=extensions,
        extension_configs=MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS
    )
    return md