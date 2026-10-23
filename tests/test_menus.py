"""Tests for the per-tenant navigation menus."""

import pytest
from django.test import RequestFactory
from simple_menu import Menu

from category.models import Category
from tenants.models import Link, Tenant


def process(tenant, name):
    request = RequestFactory().get("/all")
    request.tenant = tenant
    return Menu.process(request, name)


def child_titles(tenant, name):
    return [child.title for item in process(tenant, name) for child in item.children]


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(hostname="other", name="Other", display_name="Other", index_redirect="/all")


def test_menus_are_registered_once_for_all_tenants(tenant, other_tenant):
    process(tenant, "songbook")
    assert {"files", "songbook", "links"} <= set(Menu.items)
    assert not any(name.split("-")[0].isdigit() for name in Menu.items)


def test_categories_menu_is_scoped_to_the_tenant(tenant, other_tenant, category):
    Category.objects.create(tenant=other_tenant, name="Other Category", slug="other-cat", generate_pdf=False)

    assert "Test Category" in child_titles(tenant, "songbook")
    assert "Other Category" not in child_titles(tenant, "songbook")
    assert child_titles(other_tenant, "songbook")[0] == "Other Category"


def test_links_menu_hidden_without_links(tenant):
    assert process(tenant, "links") == []


def test_links_menu_follows_assignment_and_edits(tenant, other_tenant):
    link = Link.objects.create(link="https://example.com", display_name="Example")
    assert process(tenant, "links") == []

    tenant.links.add(link)
    assert child_titles(tenant, "links") == ["Example"]
    assert process(other_tenant, "links") == []

    link.display_name = "Renamed"
    link.save()
    assert child_titles(tenant, "links") == ["Renamed"]

    tenant.links.remove(link)
    assert process(tenant, "links") == []

    link.tenant_set.add(tenant)
    assert child_titles(tenant, "links") == ["Renamed"]
    link.tenant_set.clear()
    assert process(tenant, "links") == []

    tenant.links.add(link)
    assert child_titles(tenant, "links") == ["Renamed"]
    link.delete()
    assert process(tenant, "links") == []


def test_categories_menu_follows_all_songs_category_flag(tenant):
    tenant.all_songs_category = True
    tenant.save()
    assert "All Songs" in [str(title) for title in child_titles(tenant, "songbook")]

    tenant.all_songs_category = False
    tenant.save()
    assert "All Songs" not in [str(title) for title in child_titles(tenant, "songbook")]


def test_links_list_is_rendered_only_with_links(tenant, client):
    html = client.get("/all", HTTP_HOST="localhost").content.decode()
    assert "See Also" not in html
    lists_without_links = html.count("navbar-nav nav-left")

    tenant.links.add(Link.objects.create(link="https://example.com", display_name="Example"))
    html = client.get("/all", HTTP_HOST="localhost").content.decode()
    assert "See Also" in html
    assert html.count("navbar-nav nav-left") == lists_without_links + 1
