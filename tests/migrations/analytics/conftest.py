"""Fixtures the analytics migration tests share: tenants and the counters of their days."""

import pytest


@pytest.fixture(scope="module")
def tenants(migrate_to_start, rows):
    """Return the default tenant, which the first migration of the tenants app creates, and a second one."""
    tenant = rows("tenants.Tenant").get(hostname="localhost")
    other = rows("tenants.Tenant").create(
        hostname="other.localhost", name="Other", display_name="Other Songbook", index_redirect="/all"
    )
    return tenant, other


@pytest.fixture(scope="module")
def insert_statistic(rows):
    """Return `insert_statistic(tenant, key, hits, date)`, which adds a counter as the database has it right now."""

    def insert(tenant, key, hits, date):
        statistic = rows("analytics.DayStatistic").create(tenant_id=tenant.id, key=key, hits=hits)
        rows("analytics.DayStatistic").filter(pk=statistic.pk).update(date=date)  # date is auto_now_add
        return statistic

    return insert
