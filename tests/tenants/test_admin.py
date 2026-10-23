"""Tests for the Tenant admin."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.urls import reverse

from category.models import Category
from tenants.admin import TenantAdmin
from tenants.forms import TenantForm
from tenants.models import Tenant

pytestmark = pytest.mark.django_db


@pytest.fixture
def tenant_admin():
    return TenantAdmin(Tenant, AdminSite())


def new_tenant(**overrides):
    data = {
        "hostname": "fresh.localhost",
        "name": "Fresh",
        "display_name": "Fresh Songbook",
        "index_redirect": "/",
    }
    data.update(overrides)
    return Tenant(**data)


def test_hostname_column_links_to_the_site(tenant_admin, tenant):
    """The changelist links each tenant to its own homepage"""
    rendered = tenant_admin.hostname_link(tenant)

    assert tenant.hostname in rendered
    assert "<a href=" in rendered


def test_saving_creates_a_default_category(tenant_admin, rf, db):
    """A brand new tenant is usable right away"""
    tenant = new_tenant()

    tenant_admin.save_model(rf.get("/"), tenant, TenantForm(), change=False)

    assert Category.objects.filter(tenant=tenant, slug="default").exists()


def test_saving_points_the_index_at_the_default_category(tenant_admin, rf, db):
    """The placeholder index redirect is replaced by the default category"""
    tenant = new_tenant(index_redirect="/")

    tenant_admin.save_model(rf.get("/"), tenant, TenantForm(), change=False)

    assert tenant.index_redirect == reverse("category:index", kwargs={"slug": "default"})


def test_saving_keeps_a_configured_index_redirect(tenant_admin, rf, db):
    """A tenant that already points somewhere is left alone"""
    tenant = new_tenant(index_redirect="/all")

    tenant_admin.save_model(rf.get("/"), tenant, TenantForm(), change=False)

    assert tenant.index_redirect == "/all"


def test_saving_does_not_duplicate_categories(tenant_admin, rf, tenant, category):
    """A tenant that already has categories gets no extra default one"""
    before = Category.objects.filter(tenant=tenant).count()

    tenant_admin.save_model(rf.get("/"), tenant, TenantForm(), change=True)

    assert Category.objects.filter(tenant=tenant).count() == before


def test_changelist_renders(superuser_client, tenant):
    """The tenant changelist is reachable for site administrators"""
    assert superuser_client.get("/admin/tenants/tenant/").status_code == 200


def test_link_changelist_renders(superuser_client, tenant):
    """The link changelist is reachable for site administrators"""
    assert superuser_client.get("/admin/tenants/link/").status_code == 200
