"""Menus for backend app"""

from django.urls import reverse
from django.utils.translation import gettext_noop as _
from menu import MenuItem, Menu

from backend.auth import is_authenticated, is_localadmin, is_superadmin
from backend.models import Song
from category.models import Category

admin_children = (
    MenuItem(_("Analytics"), reverse("analytics:index")),
    MenuItem(_("Edit Songbook"), reverse("tenants:edit"), check=is_localadmin),
    MenuItem(_("Django Admin"), reverse("admin:index"), check=is_superadmin),
)

Menu.add_item(
    "admin",
    MenuItem(
        _("Admin"),
        reverse("backend:index"),
        children=admin_children,
        check=is_localadmin,
    ),
)

songbook_children = (
    MenuItem(_("Add Song"), reverse("backend:add")),
    MenuItem(Category._meta.verbose_name_plural, reverse("category:list")),
)

Menu.add_item(
    "songbook-admin",
    MenuItem(
        Song._meta.verbose_name_plural,
        reverse("backend:index"),
        children=songbook_children,
        check=is_localadmin,
    ),
)

account_children = (
    MenuItem(_("Logout"), reverse("logout"), post=True),
    MenuItem(
        _("Change password"),
        reverse("password_change"),
    ),
)

Menu.add_item(
    "account",
    MenuItem(_("Account"), reverse("login"), children=account_children, check=is_authenticated),
)


Menu.add_item(
    "qr",
    MenuItem(_("QR"), None, modal="#qrModal"),
)
