"""Tests for the analytics pages and data endpoint."""

import json
from datetime import timedelta
from unittest import mock

import pytest
from django.db import DatabaseError, IntegrityError
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.timezone import now

from analytics.models import DayStatistic

pytestmark = pytest.mark.django_db

SHOW_URL = reverse("analytics:index")
DATA_URL = reverse("analytics:data")


@pytest.fixture
def statistics(tenant):
    """Two keys with hits recorded for today and one of them a week ago too"""
    week_ago = DayStatistic.objects.create(tenant=tenant, key="rock", hits=2)
    DayStatistic.objects.filter(pk=week_ago.pk).update(date=now().date() - timedelta(days=7))  # date is auto_now_add
    DayStatistic.objects.create(tenant=tenant, key="rock", hits=5)
    DayStatistic.objects.create(tenant=tenant, key="folk", hits=3)


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


SONGS_URL = reverse("chords:songs_api")


def test_songs_request_counts_a_hit(anon_client, tenant):
    """Each request for the songs list adds a hit under the `all` key"""
    anon_client.get(SONGS_URL)
    anon_client.get(SONGS_URL)

    assert DayStatistic.objects.get(tenant=tenant, key="all").hits == 2


def test_revalidation_counts_a_hit(anon_client, tenant):
    """A 304 is an app open too"""
    etag = anon_client.get(SONGS_URL)["ETag"]

    assert anon_client.get(SONGS_URL, HTTP_IF_NONE_MATCH=etag).status_code == 304
    assert DayStatistic.objects.get(tenant=tenant, key="all").hits == 2


def test_delta_request_counts_a_hit(anon_client, tenant):
    """A request for what changed since the stored copy is counted"""
    anon_client.get(SONGS_URL)

    anon_client.get(f"{SONGS_URL}?since=0", HTTP_IF_NONE_MATCH='"other"')

    assert DayStatistic.objects.get(tenant=tenant, key="all").hits == 2


def test_hits_are_kept_per_tenant(anon_client, tenant, other_tenant):
    """Only the tenant being served is credited"""
    anon_client.get(SONGS_URL)

    assert not DayStatistic.objects.filter(tenant=other_tenant).exists()


def test_a_statistic_is_unique_per_day(tenant):
    """Two counters for one key and day cannot exist"""
    DayStatistic.objects.create(tenant=tenant, key="all")

    with pytest.raises(IntegrityError):
        DayStatistic.objects.create(tenant=tenant, key="all")


def test_hit_lost_the_race_to_create_the_counter(anon_client, tenant):
    """A counter created by a concurrent request after the first update is incremented instead"""
    DayStatistic.objects.create(tenant=tenant, key="all", hits=1)
    real_update = QuerySet.update
    calls = []

    def update(queryset, **kwargs):
        calls.append(kwargs)
        return 0 if len(calls) == 1 else real_update(queryset, **kwargs)

    with mock.patch.object(QuerySet, "update", autospec=True, side_effect=update):
        anon_client.get(SONGS_URL)

    assert DayStatistic.objects.get(tenant=tenant, key="all").hits == 2


def test_failing_counter_does_not_break_the_songs(anon_client, tenant):
    """The list is served even when the hit cannot be stored"""
    with mock.patch.object(DayStatistic.objects, "filter", side_effect=DatabaseError):
        response = anon_client.get(SONGS_URL)

    assert response.status_code == 200
