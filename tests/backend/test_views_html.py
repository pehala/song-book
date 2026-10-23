"""Tests for the song listing pages."""

import pytest
from django.test import RequestFactory
from django.urls import reverse

from backend.views import BaseSongListView

pytestmark = pytest.mark.django_db


def test_index_redirects_to_tenant_landing_page(anon_client, tenant):
    """The root path forwards to whatever the tenant configured"""
    response = anon_client.get(reverse("chords:index"))

    assert response.status_code == 302
    assert response["Location"] == tenant.index_redirect


def test_all_songs_page_renders(anon_client, song):
    """The all songs page is served as HTML"""
    response = anon_client.get(reverse("chords:all"))

    assert response.status_code == 200
    assert "songs/index.html" in [template.name for template in response.templates]


def test_all_songs_page_title_mentions_tenant(anon_client, tenant, song):
    """The page title carries the tenant display name"""
    response = anon_client.get(reverse("chords:all"))

    assert tenant.display_name in response.context["title"]


def test_all_songs_page_points_at_json_endpoint(anon_client, song):
    """The template is told where to fetch the songs from"""
    response = anon_client.get(reverse("chords:all"))

    assert response.context["data_url"] == reverse("chords:all_data")


def test_base_title_is_the_tenant_display_name(tenant):
    """The base listing falls back to the plain tenant name"""
    request = RequestFactory().get("/")
    request.tenant = tenant
    view = BaseSongListView()
    view.request = request

    assert view.get_title() == tenant.display_name


def test_page_carries_no_songs(anon_client, song):
    """The page is a shell; the songs come from the JSON endpoint only"""
    response = anon_client.get(reverse("chords:all"))

    assert "songs" not in response.context
