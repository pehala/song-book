"""Menus for PDF app"""
from django.urls import reverse
from menu import Menu, MenuItem

Menu.add_item("pdf", MenuItem("PDF",
                              reverse("pdf:export")))
