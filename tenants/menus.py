"""Generates Tenant-specific menus"""

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_menu import Menu

from pdf.cachemenuitem import CacheMenuItem, HideWhenEmptyCacheMenuItem
from tenants.menu_items import categories, distinct_requests, link_items

Menu.add_item(
    "files",
    CacheMenuItem(
        title=_("PDF"),
        url=reverse("backend:index"),
        generate_function=distinct_requests,
        cache_key=settings.PDF_CACHE_KEY,
        timeout=60 * 60,
    ),
)
Menu.add_item(
    "songbook",
    CacheMenuItem(
        title=_("Categories"),
        url=reverse("backend:index"),
        generate_function=categories,
        cache_key=settings.CATEGORY_CACHE_KEY,
        timeout=60 * 60 * 24 * 7,
    ),
)
Menu.add_item(
    "links",
    HideWhenEmptyCacheMenuItem(
        title=_("See Also"),
        url=reverse("backend:index"),
        generate_function=link_items,
        cache_key=settings.LINKS_CACHE_KEY,
        timeout=60 * 60 * 24 * 7,
    ),
)
