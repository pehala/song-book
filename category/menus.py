"""Add all available categories to the menu"""
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from menu import MenuItem, Menu

from category.models import Category
from pdf.cachemenuitem import CacheMenuItem


def categories():
    """Returns MenuItems for all Categories"""
    return [
        MenuItem(
            category["name"],
            reverse("category:index", kwargs={"slug": category["slug"]}),
            skip_translate=True,
        )
        for category in Category.objects.values("name", "slug")
    ]


Menu.add_item(
    "songbook",
    CacheMenuItem(
        title=_("Songbooks"),
        url=reverse("backend:index"),
        generate_function=categories,
        key=settings.CATEGORY_CACHE_KEY,
        timeout=60 * 60 * 24 * 7,
    ),
)
