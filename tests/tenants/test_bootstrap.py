"""Tests for the bootstrap payload the reader starts from."""

import json

import pytest
from django.core.cache import cache
from django.utils.timezone import now

from pdf.models import Status
from pdf.models.request import PDFFile
from tenants.bootstrap import SCHEMA_VERSION, bootstrap_payload
from tenants.models import Link

pytestmark = pytest.mark.django_db


def test_payload_is_json_serializable(tenant, category):
    """It is inlined into the shell as JSON"""
    assert json.loads(json.dumps(bootstrap_payload(tenant)))["v"] == SCHEMA_VERSION


def test_payload_names_the_tenant(tenant):
    """The header is drawn from the tenant's own settings"""
    payload = bootstrap_payload(tenant)

    assert (payload["name"], payload["index"], payload["all_songs"]) == (
        tenant.display_name,
        tenant.index_redirect,
        True,
    )


def test_icon_is_absent_without_a_logo(tenant):
    """No logo, no icon url"""
    assert bootstrap_payload(tenant)["icon"] is None


def test_icon_points_at_the_logo(tenant):
    """The url of the uploaded logo is passed on"""
    tenant.icon = "uploads/logo.png"
    tenant.save()

    assert bootstrap_payload(tenant)["icon"].endswith("uploads/logo.png")


def test_categories_are_listed_without_the_all_songs_entry(tenant, category):
    """Every category of the tenant is listed by slug; the all songs list is a flag instead"""
    payload = bootstrap_payload(tenant)

    assert {"slug": "test-cat", "name": "Test Category"} in payload["categories"]
    assert all(entry["slug"] != "all" for entry in payload["categories"])
    assert len(payload["categories"]) == tenant.category_set.count()


def test_categories_of_other_tenants_are_left_out(tenant, other_category):
    """Each tenant gets its own navigation"""
    assert "other-cat" not in [entry["slug"] for entry in bootstrap_payload(tenant)["categories"]]


def test_all_songs_flag_follows_the_tenant(tenant):
    """The all songs list is offered only when the tenant wants it"""
    tenant.all_songs_category = False
    tenant.save()

    assert bootstrap_payload(tenant)["all_songs"] is False


def test_new_category_shows_up_through_the_menu_cache(tenant, make_category):
    """The categories share the menu's cache entry, which category signals already clear"""
    bootstrap_payload(tenant)

    make_category(tenant, name="Fresh", slug="fresh")

    assert "fresh" in [entry["slug"] for entry in bootstrap_payload(tenant)["categories"]]


def test_links_are_listed(tenant):
    """Links of the tenant are passed on with their display name"""
    tenant.links.add(Link.objects.create(link="https://example.com", display_name="Example"))

    assert bootstrap_payload(tenant)["links"] == [{"name": "Example", "url": "https://example.com"}]


def test_files_are_listed(tenant, category):
    """The latest public finished PDF of every template is listed"""
    PDFFile.objects.create(
        tenant=tenant,
        template=category,
        filename="songbook",
        status=Status.DONE,
        public=True,
        file="pdfs/songbook.pdf",
        update_date=now(),
    )
    cache.clear()

    pdfs = bootstrap_payload(tenant)["pdfs"]

    assert pdfs == [{"name": "songbook.pdf", "url": "/media/pdfs/songbook.pdf"}]


def test_urls_point_at_the_pages_the_reader_links_to(tenant):
    """Ids are given as 0 for the client to replace"""
    urls = bootstrap_payload(tenant)["urls"]

    assert (urls["songs"], urls["me"], urls["edit"], urls["delete"], urls["hit"]) == (
        "/api/songs",
        "/api/me",
        "/edit/0",
        "/delete/0",
        "/analytics/hit/0",
    )
    assert (urls["files"], urls["templates"], urls["password"]) == (
        "/pdf/files/",
        "/pdf/templates/",
        "/accounts/password_change/",
    )
