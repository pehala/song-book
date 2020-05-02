"""Menus for backend app"""
from django.urls import reverse

from menu import MenuItem, Menu

song_children = (
    MenuItem("Add a song",
             reverse("backend:add")),
    MenuItem("Song List",
             reverse("backend:index")),
)

Menu.add_item("main", MenuItem("Songs",
                               reverse("backend:index"),
                               children=song_children))

account_children = (
    MenuItem("Log in",
             reverse("login"),
             check=lambda request: not request.user.is_authenticated),
    MenuItem("Logout",
             reverse("logout"),
             check=lambda request: request.user.is_authenticated),
    MenuItem("Change password",
             reverse("password_change"),
             check=lambda request: request.user.is_authenticated)
)

Menu.add_item("account", MenuItem("Account",
                                  reverse("login"),
                                  children=account_children))
