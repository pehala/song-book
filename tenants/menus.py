"""Generates Tenant-specific menus"""

from functools import partial

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_menu import MenuItem, Menu

from pdf.cachemenuitem import CacheMenuItem
from pdf.models.request import Status, PDFFile
from tenants.models import Tenant
from tenants.utils import create_tenant_string


def create_menus(tenant):
    """Generate menus specific for each tenant"""

    Menu.add_item(
        create_tenant_string(tenant, "files"),
        CacheMenuItem(
            title=_("PDF"),
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
            generate_function=partial(categories, tenant),
            key=create_tenant_string(tenant, settings.CATEGORY_CACHE_KEY),
            timeout=60 * 60 * 24 * 7,
        ),
    )
    links = tenant.links.all()
    if len(links) > 0:
        children = [MenuItem(link.display_name, url=link.link, skip_translate=True, new_tab=True) for link in links]
        Menu.add_item(
            create_tenant_string(tenant, "links"),
            MenuItem(
                title=_("See Also"),
                url=reverse("backend:index"),
                children=children,
            ),
        )


def categories(tenant, request):
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


def distinct_requests(request):
    """
    Not all databases can do DISTINCT ON, this is a replacement for the command below
    PDFRequest.objects.filter(file__isnull=False, status=Status.DONE).distinct("filename")[:5]

    """
    files = set()
    data = []
    for entry in PDFFile.objects.filter(
        file__isnull=False, status=Status.DONE, tenant=request.tenant, public=True
    ).exclude(file__exact=""):
        display_name = entry.name
        if display_name not in files and entry.public:
            data.append(MenuItem(display_name, entry.file.url))
            files.add(display_name)
    return data


for tenant in Tenant.objects.all().prefetch_related("links"):
    create_menus(tenant)


# pylint: disable=unused-argument
@receiver(post_save, sender=Tenant)
def generate_menus(sender, instance, created, **kwargs):
    """Generates a menu for new tenants"""
    create_menus(instance)
