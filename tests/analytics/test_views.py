"""Tests for the analytics pages and data endpoint."""

import json
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.timezone import now

from analytics.models import DayStatistic

pytestmark = pytest.mark.django_db

SHOW_URL = reverse("analytics:index")
DATA_URL = reverse("analytics:data")


@pytest.fixture
def statistics(tenant):
    """Two keys with hits recorded for today and one of them a week ago too"""
    DayStatistic.objects.create(tenant=tenant, key="rock", hits=5)
    DayStatistic.objects.create(tenant=tenant, key="folk", hits=3)
    week_ago = DayStatistic.objects.create(tenant=tenant, key="rock", hits=2)
    DayStatistic.objects.filter(pk=week_ago.pk).update(date=now().date() - timedelta(days=7))  # date is auto_now_add


def hits(client, **params):
    response = client.get(DATA_URL, params)
    assert response.status_code == 200
    return json.loads(response.content)


def test_show_page_tells_the_browser_where_the_data_is(staff_client):
    """The graph is drawn in the browser from the data endpoint"""
    response = staff_client.get(SHOW_URL)

    assert response.context["page"] == {"data": DATA_URL}
    assert b'<script id="page-data" type="application/json">' in response.content


def test_data_lists_recorded_keys(staff_client, statistics):
    """Every key that has data is offered"""
    assert hits(staff_client)["keys"] == ["folk", "rock"]


def test_data_covers_every_day_of_the_range(staff_client, statistics):
    """Days without hits are zero and today is the last day"""
    data = hits(staff_client, days=30)

    assert len(data["dates"]) == len(data["hits"]) == 30
    assert data["dates"][-1] == now().date().isoformat()
    assert data["hits"][-1] == 8
    assert data["hits"][-8] == 2
    assert sum(data["hits"]) == 10


def test_week_is_the_default_range(staff_client, statistics):
    """The hits of a week ago are one day too old for the default range"""
    data = hits(staff_client)

    assert len(data["dates"]) == 7
    assert sum(data["hits"]) == 8


def test_hits_are_returned_for_a_single_key(staff_client, statistics):
    """Only the requested key is summed up"""
    assert hits(staff_client, key="rock", days=30)["hits"][-1] == 5


def test_empty_key_sums_up_everything(staff_client, statistics):
    """An empty key aggregates across all keys"""
    assert hits(staff_client, key="")["hits"][-1] == 8


@pytest.mark.parametrize("days", ["0", "-1", "3661", "week"])
def test_invalid_range_is_rejected(staff_client, statistics, days):
    """The range is a positive number of days with a limit"""
    assert staff_client.get(DATA_URL, {"days": days}).status_code == 400


def test_other_tenants_data_is_not_returned(staff_client, tenant, other_tenant):
    """Statistics and keys are scoped to the tenant being served"""
    DayStatistic.objects.create(tenant=other_tenant, key="rock", hits=9)

    data = hits(staff_client, key="rock")

    assert data["keys"] == []
    assert sum(data["hits"]) == 0


def hit_url(key):
    return reverse("analytics:hit", kwargs={"key": key})


def test_hit_counts_a_category(anon_client, category):
    """A same-origin beacon adds a hit under the category slug"""
    response = anon_client.post(hit_url(category.slug), HTTP_ORIGIN="http://localhost")

    assert response.status_code == 204
    assert DayStatistic.objects.get(key=category.slug).hits == 1


def test_hit_counts_the_all_songs_list(anon_client, tenant):
    """The list of all songs has its own key"""
    anon_client.post(hit_url("all"), HTTP_ORIGIN="http://localhost")

    assert DayStatistic.objects.get(key="all").hits == 1


def test_repeated_hits_accumulate(anon_client, category):
    """Hits are added to the day's counter"""
    for _ in range(2):
        anon_client.post(hit_url(category.slug), HTTP_ORIGIN="http://localhost")

    assert DayStatistic.objects.get(key=category.slug).hits == 2


def test_hit_accepts_fetch_metadata_without_origin(anon_client, category):
    """Browsers that send no Origin still prove a same-origin request through Sec-Fetch-Site"""
    response = anon_client.post(hit_url(category.slug), HTTP_SEC_FETCH_SITE="same-origin")

    assert response.status_code == 204


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no origin information"),
        pytest.param({"HTTP_ORIGIN": "http://evil.example"}, id="foreign origin"),
        pytest.param({"HTTP_SEC_FETCH_SITE": "cross-site"}, id="cross-site fetch"),
    ],
)
def test_hit_from_elsewhere_is_refused(anon_client, category, headers):
    """Other sites cannot inflate the statistics"""
    assert anon_client.post(hit_url(category.slug), **headers).status_code == 403
    assert not DayStatistic.objects.exists()


def test_hit_needs_no_csrf_token(category, tenant):
    """The beacon cannot carry a CSRF token"""
    client = Client(HTTP_HOST="localhost", enforce_csrf_checks=True)

    assert client.post(hit_url(category.slug), HTTP_ORIGIN="http://localhost").status_code == 204


def test_hit_for_unknown_key_is_not_found(anon_client, tenant):
    """Only slugs of the tenant's categories can be counted"""
    assert anon_client.post(hit_url("nope"), HTTP_ORIGIN="http://localhost").status_code == 404
    assert not DayStatistic.objects.exists()


def test_hit_for_category_of_another_tenant_is_not_found(anon_client, other_category):
    """Keys are validated against the tenant being served"""
    assert anon_client.post(hit_url(other_category.slug), HTTP_ORIGIN="http://localhost").status_code == 404


def test_hit_is_post_only(anon_client, category):
    """Reading the beacon url counts nothing"""
    assert anon_client.get(hit_url(category.slug)).status_code == 405
    assert not DayStatistic.objects.exists()
