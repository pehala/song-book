"""Tags for drawing the menu"""

from django import template
from django.template.defaultfilters import stringfilter
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from backend import utils
from tenants.utils import create_tenant_string

register = template.Library()


@register.inclusion_tag("menu/bootstrap4-menu.html", takes_context=True)
def draw_menu(context, key, use_tenant=False):
    """Draws menu"""
    if use_tenant:
        key = create_tenant_string(context.request.tenant, key)
    return {"menu": context["menus"][key]}


@register.filter
@stringfilter
def prefix(value, args):
    """Adds prefix if value is not empty"""
    return str(args) + value if value else value


@register.simple_tag
def version():
    """Returns currently used version e.g. date of the last commit"""
    return utils.get_version()


@register.simple_tag
def git_revision():
    """Returns sha of the latest revision"""
    return utils.get_git_revision()


@register.simple_tag(takes_context=True)
def datatables_language(context):
    """Returns language option for currently specified language"""
    if context.request.LANGUAGE_CODE == "cs":
        url = static("datatables/cs.json")
        return mark_safe("language: {url: '%s'}," % url)
    return mark_safe("")
