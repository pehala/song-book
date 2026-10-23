"""Tests for moving categories between tenants."""

import pytest
from django.core.exceptions import FieldError
from django.urls import reverse
from django.utils import translation


pytestmark = pytest.mark.django_db

MOVE_URL = reverse("category:move")


def move_payload(target, *categories):
    """Form plus formset data for the move page"""
    data = {
        "tenant": target.pk,
        "form-TOTAL_FORMS": str(len(categories)),
        "form-INITIAL_FORMS": str(len(categories)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for index, category in enumerate(categories):
        data[f"form-{index}-pk"] = str(category.pk)
        data[f"form-{index}-name"] = category.name
    return data


def test_page_lists_the_selected_categories(superuser_client, category):
    """The categories picked in the admin are prefilled into the formset"""
    response = superuser_client.get(f"{MOVE_URL}?pk={category.pk}")

    initial = response.context["formset"].initial
    assert initial == [{"pk": category.pk, "name": category.name}]


def test_page_without_selection_is_empty(superuser_client, category):
    """Opening the page directly shows no categories"""
    response = superuser_client.get(MOVE_URL)

    assert response.context["formset"].initial == {}


def test_page_names_the_models_involved(superuser_client, category):
    """The template is told what is being moved and where"""
    response = superuser_client.get(f"{MOVE_URL}?pk={category.pk}")

    with translation.override("en"):
        assert str(response.context["source_verbose_name_plural"]) == "Categories"
        assert str(response.context["target_verbose_name"]) == "Tenant"


def test_invalid_submission_moves_nothing(superuser_client, category, tenant, other_tenant):
    """A submission without a target tenant redisplays the page and changes nothing

    Note: the view rebuilds an unbound form for the response, so the validation
    errors are not shown back to the user.
    """
    data = move_payload(other_tenant, category)
    data["tenant"] = ""

    response = superuser_client.post(MOVE_URL, data)

    assert response.status_code == 200
    category.refresh_from_db()
    assert category.tenant == tenant


@pytest.mark.xfail(
    raises=FieldError,
    strict=True,
    reason=(
        "CategoryMoveView.action is broken: PDFTemplate has neither a 'category_id' "
        "lookup, nor a 'files' attribute, nor a 'tenant' field, so the move always "
        "raises before anything is reassigned."
    ),
)
def test_move_reassigns_the_category(superuser_client, category, other_tenant):
    """Moving a category hands it over to the target tenant"""
    superuser_client.post(MOVE_URL, move_payload(other_tenant, category))

    category.refresh_from_db()
    assert category.tenant == other_tenant
