"""The navigation entries of a tenant, which the header is drawn from."""

from django.conf import settings

from tenants.cachedmenu import CachedMenu
from tenants.menu_items import categories, distinct_requests, link_items

FILES_MENU = CachedMenu(generate_function=distinct_requests, cache_key=settings.PDF_CACHE_KEY, timeout=60 * 60)
CATEGORIES_MENU = CachedMenu(
    generate_function=categories, cache_key=settings.CATEGORY_CACHE_KEY, timeout=60 * 60 * 24 * 7
)
LINKS_MENU = CachedMenu(generate_function=link_items, cache_key=settings.LINKS_CACHE_KEY, timeout=60 * 60 * 24 * 7)
