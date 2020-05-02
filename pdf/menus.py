"""Menus for PDF app"""
from django.templatetags.static import static
from django.urls import reverse
from menu import Menu, MenuItem

song_children = (
    MenuItem("Czech",
             static("songbook-cs.pdf")),
    MenuItem("English",
             static("songbook-en.pdf")),
)

Menu.add_item("pdf", MenuItem("PDF",
                              reverse("backend:index"),
                              children=song_children))
