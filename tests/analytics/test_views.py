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


def timestamp(days_ago=0):
    return str(int((now() - timedelta(days=days_ago)).timestamp()))


@pytest.fixture
def statistics(tenant):
    """Two keys with hits recorded for today"""
    DayStatistic.objects.create(tenant=tenant, key="rock", hits=5)
    DayStatistic.objects.create(tenant=tenant, key="folk", hits=3)


def test_show_page_lists_recorded_keys(staff_client, statistics):
    """The graph page offers every key that has data"""
    keys = list(staff_client.get(SHOW_URL).context["keys"])

    assert sorted(keys) == ["folk", "rock"]


@pytest.mark.parametrize("name", ["now", "week", "month", "year"])
def test_show_page_offers_date_ranges(staff_client, statistics, name):
    """The page provides the boundaries of every preset range"""
    assert staff_client.get(SHOW_URL).context[name] is not None


def test_show_page_ignores_other_tenants(staff_client, other_tenant):
    """Keys recorded for another tenant are not offered"""
    DayStatistic.objects.create(tenant=other_tenant, key="foreign", hits=1)

    assert list(staff_client.get(SHOW_URL).context["keys"]) == []


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="nothing submitted"),
        pytest.param({"key": "rock"}, id="without start_date"),
        pytest.param({"start_date": "0"}, id="without key"),
    ],
)
def test_incomplete_requests_are_rejected(staff_client, statistics, payload):
    """Both the start date and the key are mandatory"""
    assert staff_client.post(DATA_URL, payload).status_code == 400


def test_hits_are_returned_for_a_single_key(staff_client, statistics):
    """Only the requested key is summed up"""
    response = staff_client.post(DATA_URL, {"start_date": timestamp(days_ago=1), "key": "rock"})

    assert list(json.loads(response.content).values()) == [5]


def test_empty_key_sums_up_everything(staff_client, statistics):
    """An empty key aggregates across all keys"""
    response = staff_client.post(DATA_URL, {"start_date": timestamp(days_ago=1), "key": ""})

    assert list(json.loads(response.content).values()) == [8]


def test_end_date_limits_the_range(staff_client, statistics):
    """Days after the end date are left out"""
    response = staff_client.post(
        DATA_URL,
        {"start_date": timestamp(days_ago=10), "end_date": timestamp(days_ago=5), "key": "rock"},
    )

    assert json.loads(response.content) == {}


def test_other_tenants_data_is_not_returned(staff_client, other_tenant):
    """Statistics are scoped to the tenant being served"""
    DayStatistic.objects.create(tenant=other_tenant, key="rock", hits=9)

    response = staff_client.post(DATA_URL, {"start_date": timestamp(days_ago=1), "key": "rock"})

    assert json.loads(response.content) == {}


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
