"""Menus for PDF app"""
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from menu import Menu, MenuItem

from pdf.models import PDFRequest, Status


def distinct_requests():
    """
    Not all databases can do DISTINCT ON, this is a replacement for the command below
    PDFRequest.objects.filter(file__isnull=False, status=Status.DONE).distinct("filename")[:5]

    """
    files = []
    data = []
    for entry in PDFRequest.objects.filter(file__isnull=False, status=Status.DONE):
        if entry.filename not in files:
            files.append(entry.filename)
            data.append(entry)
    return data


pdf_children = (
    MenuItem(_("Create new PDF"),
             reverse("pdf:new")),
    MenuItem(_("PDF Requests"),
             reverse("pdf:list")),
)

Menu.add_item("pdf", MenuItem(_("PDF"),
                              reverse("backend:index"),
                              children=pdf_children,
                              check=lambda request: request.user.is_authenticated))

files_children = [MenuItem(request.filename, request.file.url)
                  for request
                  in distinct_requests()]
Menu.add_item("files", MenuItem(_("Files"),
                                reverse("backend:index"),
                                children=files_children))
