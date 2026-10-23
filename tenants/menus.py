"""Generates Tenant-specific menus"""

from functools import partial

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_menu import Menu, MenuItem

from pdf.cachemenuitem import CacheMenuItem
from tenants.menu_items import categories, distinct_requests
from tenants.models import Tenant
from tenants.utils import tenant_cache_key


def create_menus(tenant):
    """Generate menus specific for each tenant"""

    Menu.add_item(
        tenant_cache_key(tenant, "files"),
        CacheMenuItem(
            title=_("PDF"),
            url=reverse("backend:index"),
            generate_function=partial(distinct_requests, tenant),
            key=tenant_cache_key(tenant, settings.PDF_CACHE_KEY),
            timeout=60 * 60,
        ),
    )
    Menu.add_item(
        tenant_cache_key(tenant, "songbook"),
        CacheMenuItem(
            title=_("Categories"),
            url=reverse("backend:index"),
            generate_function=partial(categories, tenant),
            key=tenant_cache_key(tenant, settings.CATEGORY_CACHE_KEY),
            timeout=60 * 60 * 24 * 7,
        ),
    )
    links = tenant.links.all()
    if len(links) > 0:
        children = [MenuItem(link.display_name, url=link.link, skip_translate=True, new_tab=True) for link in links]
        Menu.add_item(
            tenant_cache_key(tenant, "links"),
            MenuItem(
                title=_("See Also"),
                url=reverse("backend:index"),
                children=children,
            ),
        )


for tenant in Tenant.objects.all().prefetch_related("links"):
    create_menus(tenant)


@receiver(post_save, sender=Tenant)
def generate_menus(sender, instance, created, **kwargs):
    """Generates a menu for new tenants"""
    create_menus(instance)
