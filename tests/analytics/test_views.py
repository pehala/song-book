"""Tests for the analytics pages and data endpoint."""

import json
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils.timezone import now

from analytics.models import DayStatistic
from analytics.views import AnalyticsMixin

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


def test_views_without_their_own_key_are_counted_as_general():
    """A view that does not name itself is recorded under the default key"""
    assert AnalyticsMixin().get_key() == "General"
