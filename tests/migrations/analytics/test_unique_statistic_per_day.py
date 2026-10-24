"""Migration `0006_unique_statistic_per_day`, which allows one counter per tenant, key and day.

Counters are inserted at the migration before it, some of them twice for one day, as concurrent first hits of
a day could leave them. The migration runs, and every duplicate has to be folded into the oldest counter of
its day without losing a hit.
"""

from datetime import timedelta

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils.timezone import now

SOURCE = ("analytics", "0005_alter_daystatistic_hits")
TARGET = ("analytics", "0006_unique_statistic_per_day")

TODAY = now().date()
YESTERDAY = TODAY - timedelta(days=1)
CONSTRAINT = "unique_statistic_per_day"


@pytest.fixture(scope="module")
def migration_target():
    """Migrate from the migration before the constraint to the one that adds it."""
    return SOURCE, TARGET


@pytest.fixture(scope="module")
def create_old_data(migrate_to_start, tenants, insert_statistic):
    """Insert counters, three for one day of a key, two for a day of another tenant, and ones without a twin."""
    tenant, other = tenants
    return {
        "first": insert_statistic(tenant, "all", 1, TODAY),
        "second": insert_statistic(tenant, "all", 2, TODAY),
        "third": insert_statistic(tenant, "all", 4, TODAY),
        "other_first": insert_statistic(other, "all", 8, TODAY),
        "other_second": insert_statistic(other, "all", 16, TODAY),
        "category_first": insert_statistic(tenant, "cs", 32, YESTERDAY),
        "category_second": insert_statistic(tenant, "cs", 64, YESTERDAY),
        "yesterday": insert_statistic(tenant, "all", 128, YESTERDAY),
        "folk": insert_statistic(tenant, "folk", 256, TODAY),
    }


def hits(rows, tenant, key, date):
    return list(
        rows("analytics.DayStatistic").filter(tenant_id=tenant.id, key=key, date=date).values_list("hits", flat=True)
    )


def test_upgrade_folds_the_duplicates_into_the_oldest_counter(rows, tenants, create_old_data):
    """The counter that survives is the first one, holding the hits of all of them."""
    tenant, _ = tenants

    survivor = rows("analytics.DayStatistic").get(tenant_id=tenant.id, key="all", date=TODAY)

    assert (survivor.pk, survivor.hits) == (create_old_data["first"].pk, 7)


def test_upgrade_keeps_tenants_apart(rows, tenants):
    """The same key and day of another tenant is folded on its own."""
    _, other = tenants

    assert hits(rows, other, "all", TODAY) == [24]


def test_upgrade_folds_other_days_and_keys_on_their_own(rows, tenants):
    """A key is folded within its day, and a counter on another day or key stays as it was."""
    tenant, _ = tenants

    assert hits(rows, tenant, "cs", YESTERDAY) == [96]
    assert hits(rows, tenant, "all", YESTERDAY) == [128]
    assert hits(rows, tenant, "folk", TODAY) == [256]


def test_upgrade_keeps_every_hit(rows):
    """The hits of all counters add up to what they did before."""
    total = sum(rows("analytics.DayStatistic").values_list("hits", flat=True))

    assert total == sum(2**exponent for exponent in range(9))


def test_a_day_has_one_counter(rows, tenants):
    """The database refuses a second counter for a key and day."""
    tenant, _ = tenants

    with pytest.raises(IntegrityError), transaction.atomic():
        rows("analytics.DayStatistic").create(tenant_id=tenant.id, key="all")


def test_downgrade_drops_the_constraint_and_keeps_the_counters(migrate, rows, tenants):
    """Without the constraint a day may have two counters again, and the folded ones are as they were."""
    tenant, _ = tenants
    migrate(SOURCE)
    try:
        assert CONSTRAINT not in connection.introspection.get_constraints(connection.cursor(), "analytics_daystatistic")
        assert hits(rows, tenant, "all", TODAY) == [7]
    finally:
        migrate(TARGET)
