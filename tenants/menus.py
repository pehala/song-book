"""Generates Tenant-specific menus"""
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from simple_menu import MenuItem, Menu

from category.models import Category
from pdf.cachemenuitem import CacheMenuItem
from pdf.models.request import PDFRequest, Status

from tenants.models import Tenant
from tenants.utils import create_tenant_string


def categories(request):
    """Returns MenuItems for all Categories"""
    return [
        MenuItem(
            category["name"],
            reverse("category:index", kwargs={"slug": category["slug"]}),
            skip_translate=True,
        )
        for category in Category.objects.filter(tenant=request.tenant).values("name", "slug")
    ]


def distinct_requests(request):
    """
    Not all databases can do DISTINCT ON, this is a replacement for the command below
    PDFRequest.objects.filter(file__isnull=False, status=Status.DONE).distinct("filename")[:5]

    """
    files = set()
    data = []
    for entry in PDFRequest.objects.filter(file__isnull=False, status=Status.DONE, tenant=request.tenant).exclude(
        file__exact=""
    ):
        # pylint: disable=protected-access
        if entry.filename not in files and entry.public:
            data.append(MenuItem(entry.filename, entry.file.url))
            files.add(entry.filename)
    return data


for tenant in Tenant.objects.all():
    Menu.add_item(
        create_tenant_string(tenant, "files"),
        CacheMenuItem(
            title=_("Files"),
            url=reverse("backend:index"),
            generate_function=distinct_requests,
            key=create_tenant_string(tenant, settings.PDF_CACHE_KEY),
            timeout=60 * 60,
        ),
    )
    Menu.add_item(
        create_tenant_string(tenant, "songbook"),
        CacheMenuItem(
            title=_("Categories"),
            url=reverse("backend:index"),
            generate_function=categories,
            key=create_tenant_string(tenant, settings.CATEGORY_CACHE_KEY),
            timeout=60 * 60 * 24 * 7,
        ),
    )
