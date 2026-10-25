"""Generators for the items of the tenant-specific menus"""

from django.db.models import Prefetch

from category.models import Category
from pdf.models.request import AllSongsTemplate, ManualPDFTemplate, PDFFile, Status


def categories(tenant):
    """Returns the slug and name of every Category of the tenant"""
    return [{"slug": category.slug, "name": category.name} for category in tenant.category_set.all()]


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
    for model in [Category, ManualPDFTemplate, AllSongsTemplate]:
        for template in model.objects.filter(tenant=tenant).prefetch_related(latest_files_prefetch):
            file = template.prefetched_files[0] if template.prefetched_files else None
            if file and file.file:
                data.append({"name": file.name, "url": file.file.url})
    # Without template
    for file in PDFFile.objects.filter(tenant=tenant, status=Status.DONE, public=True, template=None):
        if file.file:
            data.append({"name": file.name, "url": file.file.url})
    return data


def link_items(tenant):
    """Returns the name and url of every Link of the Tenant"""
    return [{"name": link.display_name, "url": link.link} for link in tenant.links.all()]
