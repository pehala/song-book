"""Menus for backend app"""
from django.urls import reverse
from django.utils.translation import gettext_noop as _

from menu import MenuItem, Menu

admin_children = (
    MenuItem(_("Songbook List"),
             reverse("category:list")),
    MenuItem(_("Add a song"),
             reverse("backend:add")),
    MenuItem(_("Add Songbook"),
             reverse("category:add")),
    MenuItem(_("Analytics"),
             reverse("analytics:index"))
)

Menu.add_item("admin", MenuItem(_("Admin"),
                                reverse("backend:index"),
                                children=admin_children,
                                check=lambda request: request.user.is_authenticated))

account_children = (
    MenuItem(_("Log in"),
             reverse("login"),
             check=lambda request: not request.user.is_authenticated),
    MenuItem(_("Logout"),
             reverse("logout"),
             check=lambda request: request.user.is_authenticated),
    MenuItem(_("Change password"),
             reverse("password_change"),
             check=lambda request: request.user.is_authenticated)
)

Menu.add_item("account", MenuItem(_("Account"),
                                  reverse("login"),
                                  children=account_children))
