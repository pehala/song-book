"""Tests shared by the pages that move categories and PDF templates to another tenant.

What only one of them does is asserted in `category/test_views_move.py` and `pdf/test_views_templates.py`.
"""

import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db


def move_payload(target, *objects):
    """Form plus formset data for a move page."""
    data = {
        "tenant": target.pk,
        "form-TOTAL_FORMS": str(len(objects)),
        "form-INITIAL_FORMS": str(len(objects)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for index, moved in enumerate(objects):
        data[f"form-{index}-pk"] = str(moved.pk)
        data[f"form-{index}-name"] = moved.name
    return data


@pytest.fixture(
    params=[
        pytest.param(("category:move", "category"), id="category"),
        pytest.param(("pdf:templates:move", "manual_template"), id="manual template"),
    ]
)
def move(request):
    """The url of a move page and an object it moves."""
    name, fixture = request.param
    return reverse(name), request.getfixturevalue(fixture)


def test_move_reassigns_the_object(superuser_client, move, other_tenant):
    """The moved object is handed over to the target tenant."""
    url, moved = move

    response = superuser_client.post(url, move_payload(other_tenant, moved))

    assert response.status_code == 302
    moved.refresh_from_db()
    assert moved.tenant == other_tenant


def test_move_takes_the_generated_files_along(superuser_client, move, make_pdf_file, other_tenant):
    """Files printed from the moved object follow it to the new tenant."""
    url, moved = move
    file = make_pdf_file(moved)

    superuser_client.post(url, move_payload(other_tenant, moved))

    file.refresh_from_db()
    assert file.tenant == other_tenant


def test_move_drops_the_files_menu_of_both_tenants(superuser_client, move, tenant, other_tenant):
    """The files leave the menu of one tenant and enter the menu of the other."""
    url, moved = move
    for each in (tenant, other_tenant):
        cache.set(tenant_cache_key(each, settings.PDF_CACHE_KEY), ["stale"], 60)

    superuser_client.post(url, move_payload(other_tenant, moved))

    for each in (tenant, other_tenant):
        assert cache.get(tenant_cache_key(each, settings.PDF_CACHE_KEY)) is None
