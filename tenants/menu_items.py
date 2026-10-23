"""Generators for the items of the tenant-specific menus"""

from django.db.models import Prefetch
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_menu import MenuItem

from category.models import Category
from pdf.models.request import ManualPDFTemplate, PDFFile, Status


def categories(tenant):
    """Returns MenuItems for all Categories"""
    items = [
        MenuItem(
            category.name,
            reverse("category:index", kwargs={"slug": category.slug}),
            skip_translate=True,
        )
        for category in tenant.category_set.all()
    ]
    if tenant.all_songs_category:
        items.append(MenuItem(title=_("All Songs"), url=reverse("backend:all"), separator=True, skip_translate=False))
    return items


def distinct_requests(tenant):
    """
    Not all databases can do DISTINCT ON, this is a replacement for the command below
    PDFRequest.objects.filter(file__isnull=False, status=Status.DONE).distinct("filename")[:5]

    """
    latest_files_prefetch = Prefetch(
        "pdffile_set",
        queryset=PDFFile.objects.filter(status=Status.DONE, public=True).order_by("-update_date")[:1],
        to_attr="prefetched_files",
    )
    data = []
    for model in [Category, ManualPDFTemplate]:
        for template in model.objects.filter(tenant=tenant).prefetch_related(latest_files_prefetch):
            file = template.prefetched_files[0] if template.prefetched_files else None
            if file and file.file:
                data.append(MenuItem(file.name, file.file.url))
    # Without template
    for file in PDFFile.objects.filter(tenant=tenant, status=Status.DONE, public=True, template=None):
        if file.file:
            data.append(MenuItem(file.name, file.file.url))
    return data


def link_items(tenant):
    """Returns MenuItems for all Links of the Tenant"""
    return [
        MenuItem(link.display_name, url=link.link, skip_translate=True, new_tab=True) for link in tenant.links.all()
    ]
