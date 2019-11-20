from django.urls import reverse

from menu import MenuItem, Menu

llamas_children = (
    MenuItem("Add a song",
             reverse("backend:add")),
    MenuItem("Song List",
             reverse("backend:index"))
)

Menu.add_item("main", MenuItem("Songs",
                               reverse("backend:index"),
                               children=llamas_children))

children = (
    MenuItem("Log in",
             reverse("login"),
             check=lambda request: not request.user.is_authenticated),
    MenuItem("Logout",
             reverse("logout"),
             check=lambda request: request.user.is_authenticated)
)

Menu.add_item("account", MenuItem("Account",
                                  reverse("login"),
                                  children=children))