"""Tags for drawing the menu"""

from django import template
from django.template.defaultfilters import stringfilter
from django.templatetags.static import static
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
@stringfilter
def prefix(value, args):
    """Adds prefix if value is not empty"""
    return str(args) + value if value else value


@register.simple_tag(takes_context=True)
def datatables_language(context):
    """Returns language option for currently specified language"""
    if context.request.LANGUAGE_CODE == "cs":
        url = static("datatables/cs.json")
        return mark_safe(f"language: {{url: '{url}'}},")
    return mark_safe("")
