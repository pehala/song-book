"""Menus for PDF app"""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from menu import Menu, MenuItem

from backend.auth import is_localadmin
from pdf.models.request import ManualPDFTemplate, PDFFile

pdf_children = (
    MenuItem(
        _("Generated %(files)s") % {"files": PDFFile._meta.verbose_name_plural},
        reverse("pdf:files:list"),
        skip_translate=True,
    ),
    MenuItem(ManualPDFTemplate._meta.verbose_name_plural, reverse("pdf:templates:list"), skip_translate=True),
)

Menu.add_item(
    "pdf",
    MenuItem(
        _("Files"),
        reverse("backend:index"),
        children=pdf_children,
        check=is_localadmin,
    ),
)
