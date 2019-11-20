from django import template
from django.template.defaultfilters import stringfilter
from markdownx.utils import markdownify

register = template.Library()


@register.filter
@stringfilter
def show_markdown(text):
    return markdownify(text)
