"""Tags for drawing the menu"""
from django import template

from tenants.utils import create_tenant_string

register = template.Library()


@register.inclusion_tag("menu/bootstrap4-menu.html", takes_context=True)
def draw_menu(context, key, use_tenant=False):
    """Draws menu"""
    if use_tenant:
        key = create_tenant_string(context.request.tenant, key)
    return {"menu": context["menus"][key]}
