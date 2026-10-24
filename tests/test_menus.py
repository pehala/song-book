"""Tests for the per-tenant navigation entries."""

import pytest

from category.models import Category
from tenants.menus import CATEGORIES_MENU, LINKS_MENU
from tenants.models import Link


def titles(menu, tenant):
    return [str(item.title) for item in menu.children_of(tenant)]


def test_categories_are_scoped_to_the_tenant(tenant, other_tenant, category):
    Category.objects.create(tenant=other_tenant, name="Other Category", slug="other-cat", generate_pdf=False)

    assert "Test Category" in titles(CATEGORIES_MENU, tenant)
    assert "Other Category" not in titles(CATEGORIES_MENU, tenant)
    assert titles(CATEGORIES_MENU, other_tenant)[0] == "Other Category"


def test_links_are_empty_without_links(tenant):
    assert LINKS_MENU.children_of(tenant) == []


def test_links_follow_assignment_and_edits(tenant, other_tenant):
    link = Link.objects.create(link="https://example.com", display_name="Example")
    assert LINKS_MENU.children_of(tenant) == []

    tenant.links.add(link)
    assert titles(LINKS_MENU, tenant) == ["Example"]
    assert LINKS_MENU.children_of(other_tenant) == []

    link.display_name = "Renamed"
    link.save()
    assert titles(LINKS_MENU, tenant) == ["Renamed"]

    tenant.links.remove(link)
    assert LINKS_MENU.children_of(tenant) == []

    link.tenant_set.add(tenant)
    assert titles(LINKS_MENU, tenant) == ["Renamed"]
    link.tenant_set.clear()
    assert LINKS_MENU.children_of(tenant) == []

    tenant.links.add(link)
    assert titles(LINKS_MENU, tenant) == ["Renamed"]
    link.delete()
    assert LINKS_MENU.children_of(tenant) == []


def test_categories_follow_all_songs_category_flag(tenant):
    tenant.all_songs_category = True
    tenant.save()
    assert "All Songs" in titles(CATEGORIES_MENU, tenant)

    tenant.all_songs_category = False
    tenant.save()
    assert "All Songs" not in titles(CATEGORIES_MENU, tenant)


@pytest.mark.django_db
def test_header_of_server_pages_lists_links_only_when_there_are_some(tenant, client):
    """The links reach the pages the server renders through the header's inlined bootstrap"""
    html = client.get("/accounts/login/", HTTP_HOST="localhost").content.decode()
    assert "https://example.com" not in html

    tenant.links.add(Link.objects.create(link="https://example.com", display_name="Example"))
    html = client.get("/accounts/login/", HTTP_HOST="localhost").content.decode()
    assert "https://example.com" in html
