"""Add all available categories to the menu"""
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from menu import MenuItem, Menu

from category.models import Category

children = [MenuItem(category["name"], reverse("category:index",
                                               kwargs={"slug": category["slug"]}), skip_translate=True)
            for category
            in Category.objects.values("name", "slug")]

Menu.add_item("songbook", MenuItem(_("Song books"),
                                   reverse("backend:index"),
                                   children=children))
