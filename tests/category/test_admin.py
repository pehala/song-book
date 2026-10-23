"""Tests for the Category admin."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.urls import reverse

from category.admin import CategoryAdmin
from category.models import Category

pytestmark = pytest.mark.django_db


@pytest.fixture
def category_admin():
    return CategoryAdmin(Category, AdminSite())


def test_tenant_column_links_to_the_tenant(category_admin, category, tenant):
    """The changelist links each category to its owning tenant"""
    rendered = category_admin.tenant_name(category)

    assert reverse("admin:tenants_tenant_change", args=[tenant.id]) in rendered
    assert tenant.name in rendered


def test_move_action_redirects_to_the_move_page(category_admin, category, rf):
    """The bulk action hands the selection over to the move view"""
    response = category_admin.move_tenant(rf.get("/"), Category.objects.filter(pk=category.pk))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("category:move"))
    assert f"pk={category.pk}" in response["Location"]


def test_changelist_renders(superuser_client, category):
    """The category changelist is reachable for site administrators"""
    assert superuser_client.get("/admin/category/category/").status_code == 200
