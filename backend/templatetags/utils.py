"""Tags for the datatables pages"""

from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def datatables_language(context):
    """Returns language option for currently specified language"""
    if context.request.LANGUAGE_CODE == "cs":
        url = static("datatables/cs.json")
        return mark_safe(f"language: {{url: '{url}'}},")
    return mark_safe("")
