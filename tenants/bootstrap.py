"""The data the reader needs before it can draw anything: navigation, links and URLs"""

from django.urls import reverse

from backend.utils import get_git_revision, get_version
from tenants.menus import CATEGORIES_ITEM, FILES_ITEM, LINKS_ITEM

SCHEMA_VERSION = 1


def named_urls():
    """URLs of the pages the reader links to; `0` stands for the id or key the client fills in"""
    return {
        "login": reverse("login"),
        "logout": reverse("logout"),
        "setlang": reverse("set_language"),
        "songs": reverse("chords:songs_api"),
        "me": reverse("chords:me"),
        "hit": reverse("analytics:hit", kwargs={"key": "0"}),
        "add": reverse("backend:add"),
        "edit": reverse("backend:edit", kwargs={"pk": 0}),
        "delete": reverse("backend:delete", kwargs={"pk": 0}),
        "categories": reverse("category:list"),
        "analytics": reverse("analytics:index"),
        "tenant": reverse("tenants:edit"),
        "admin": reverse("admin:index"),
        "files": reverse("pdf:files:list"),
        "templates": reverse("pdf:templates:list"),
        "password": reverse("password_change"),
    }


def bootstrap_payload(tenant):
    """
    Returns the JSON-serializable bootstrap of the tenant's reader.

    Categories, PDFs and links come from the entries the navigation menus keep in the cache,
    so whatever invalidates the menus invalidates this too.
    """
    return {
        "v": SCHEMA_VERSION,
        "name": tenant.display_name,
        "icon": tenant.icon.url if tenant.icon else None,
        "index": tenant.index_redirect,
        "all_songs": tenant.all_songs_category,
        "categories": [
            {"slug": item.category_slug, "name": item.title}
            for item in CATEGORIES_ITEM.children_of(tenant)
            if hasattr(item, "category_slug")
        ],
        "pdfs": [{"name": item.title, "url": item.url} for item in FILES_ITEM.children_of(tenant)],
        "links": [{"name": item.title, "url": item.url} for item in LINKS_ITEM.children_of(tenant)],
        "urls": named_urls(),
        "version": get_version(),
        "rev": get_git_revision(),
    }
