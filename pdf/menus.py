"""Menus for PDF app"""
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from menu import Menu, MenuItem

from backend.auth import is_localadmin

pdf_children = (
    MenuItem(_("Create PDF"), reverse("pdf:new")),
    MenuItem(_("PDF Requests"), reverse("pdf:list")),
)

Menu.add_item(
    "pdf",
    MenuItem(
        _("PDF"),
        reverse("backend:index"),
        children=pdf_children,
        check=is_localadmin,
    ),
)
