"""Generates Tenant-specific menus"""

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_menu import Menu

from pdf.cachemenuitem import CacheMenuItem, HideWhenEmptyCacheMenuItem
from tenants.menu_items import categories, distinct_requests, link_items


def index_url(request):
    """The parent items link to the index; resolved per request so importing this module needs no URLconf"""
    return reverse("backend:index")


FILES_ITEM = CacheMenuItem(
    title=_("PDF"),
    url=index_url,
    generate_function=distinct_requests,
    cache_key=settings.PDF_CACHE_KEY,
    timeout=60 * 60,
)
CATEGORIES_ITEM = CacheMenuItem(
    title=_("Categories"),
    url=index_url,
    generate_function=categories,
    cache_key=settings.CATEGORY_CACHE_KEY,
    timeout=60 * 60 * 24 * 7,
)
LINKS_ITEM = HideWhenEmptyCacheMenuItem(
    title=_("See Also"),
    url=index_url,
    generate_function=link_items,
    cache_key=settings.LINKS_CACHE_KEY,
    timeout=60 * 60 * 24 * 7,
)

Menu.add_item("files", FILES_ITEM)
Menu.add_item("songbook", CATEGORIES_ITEM)
Menu.add_item("links", LINKS_ITEM)
