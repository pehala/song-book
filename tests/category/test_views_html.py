"""Tests for the per-category song listing page."""

import pytest
from django.urls import reverse

from analytics.models import DayStatistic

pytestmark = pytest.mark.django_db


def url_for(category):
    return reverse("category:index", kwargs={"slug": category.slug})


def test_page_renders(anon_client, category, song):
    """The category page is served as HTML"""
    response = anon_client.get(url_for(category))

    assert response.status_code == 200
    assert "songs/index.html" in [template.name for template in response.templates]


def test_unknown_slug_returns_404(anon_client, tenant):
    """A slug without a category does not exist"""
    assert anon_client.get(reverse("category:index", kwargs={"slug": "nope"})).status_code == 404


def test_category_of_another_tenant_returns_404(anon_client, other_category):
    """Categories are not reachable across tenants"""
    assert anon_client.get(url_for(other_category)).status_code == 404


def test_title_mentions_category_and_tenant(anon_client, tenant, category, song):
    """The page title carries both names"""
    title = anon_client.get(url_for(category)).context["title"]

    assert category.name in title
    assert tenant.display_name in title


def test_page_points_at_json_endpoint(anon_client, category, song):
    """The template is told where to fetch the songs from"""
    response = anon_client.get(url_for(category))

    assert response.context["data_url"] == reverse("category:songs_data", kwargs={"slug": category.slug})


def test_page_carries_no_songs(anon_client, category, song):
    """The page is a shell; the songs come from the JSON endpoint only"""
    response = anon_client.get(url_for(category))

    assert "songs" not in response.context


def test_visit_is_counted(anon_client, category, song):
    """Opening a category records an analytics hit under its slug"""
    anon_client.get(url_for(category))

    assert DayStatistic.objects.get(key=category.slug).hits == 1


def test_repeated_visits_accumulate(anon_client, category, song):
    """Hits are added to the existing counter for the day"""
    anon_client.get(url_for(category))
    anon_client.get(url_for(category))

    assert DayStatistic.objects.get(key=category.slug).hits == 2


def test_json_fetch_is_not_counted_again(anon_client, category, song):
    """The page's own JSON request does not add a second hit"""
    anon_client.get(url_for(category))
    anon_client.get(reverse("category:songs_data", kwargs={"slug": category.slug}))

    assert DayStatistic.objects.get(key=category.slug).hits == 1
