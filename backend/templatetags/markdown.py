from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import escape
from markdownx.utils import markdownify

register = template.Library()


@register.filter
@stringfilter
def show_markdown(text):
    return markdownify(escape(text))
