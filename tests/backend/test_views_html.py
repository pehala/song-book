"""Tests for the song listing pages."""

import json

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


def test_archived_songs_are_numbered_last(superuser_client, song, archived_song):
    """Superusers see archived songs, but only after the active ones"""
    response = superuser_client.get(reverse("chords:all"))

    songs = json.loads(response.context["songs"])
    numbers = {entry["name"]: entry["number"] for entry in songs}
    assert numbers["Test Song"] < numbers["Archived Song"]


def test_songs_of_other_tenants_are_not_listed(anon_client, song, other_category, make_song):
    """Songs reachable only through another tenant's category stay hidden"""
    make_song(other_category, name="Foreign Song")

    response = anon_client.get(reverse("chords:all"))

    names = [entry["name"] for entry in json.loads(response.context["songs"])]
    assert "Foreign Song" not in names
    assert "Test Song" in names
