"""Tests for moving categories between tenants."""

import pytest
from django.urls import reverse
from django.utils import translation
from django.utils.timezone import now

from backend.models import Song
from category.models import Category
from pdf.models.request import PDFFile

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


def test_move_reassigns_the_category(superuser_client, category, other_tenant):
    """Moving a category hands it over to the target tenant"""
    response = superuser_client.post(MOVE_URL, move_payload(other_tenant, category))

    assert response.status_code == 302
    category.refresh_from_db()
    assert category.tenant == other_tenant


def test_move_takes_the_generated_files_along(superuser_client, category, pdf_file, other_tenant):
    """Files printed from the category follow it to the new tenant"""
    superuser_client.post(MOVE_URL, move_payload(other_tenant, category))

    pdf_file.refresh_from_db()
    assert pdf_file.tenant == other_tenant


def test_move_leaves_other_tenants_files_alone(superuser_client, category, other_tenant, tenant):
    """Files of a category that stays behind keep their tenant"""
    staying = Category.objects.create(
        tenant=tenant, name="Staying", slug="staying", generate_pdf=False, filename="stay", locale="en"
    )
    file = PDFFile.objects.create(tenant=tenant, template=staying, filename="stay", update_date=now())

    superuser_client.post(MOVE_URL, move_payload(other_tenant, category))

    file.refresh_from_db()
    assert file.tenant == tenant


def test_move_takes_the_songs_along(superuser_client, category, song, other_tenant):
    """A song living only in the moved category moves with it"""
    superuser_client.post(MOVE_URL, move_payload(other_tenant, category))

    song.refresh_from_db()
    assert list(song.categories.all()) == [category]
    assert Song.objects.count() == 1


def test_song_in_two_tenants_is_split(superuser_client, category, song, make_category, other_tenant):
    """A song that also lives in a category staying behind is duplicated"""
    staying = make_category(category.tenant, name="Staying", slug="staying")
    song.categories.add(staying)

    superuser_client.post(MOVE_URL, move_payload(other_tenant, category))

    song.refresh_from_db()
    copy = Song.objects.exclude(pk=song.pk).get(name=song.name)
    assert list(song.categories.all()) == [category]
    assert list(copy.categories.all()) == [staying]


def test_splitting_keeps_the_lyrics(superuser_client, category, song, make_category, other_tenant):
    """The copy left behind is a faithful duplicate"""
    staying = make_category(category.tenant, name="Staying", slug="staying")
    song.categories.add(staying)

    superuser_client.post(MOVE_URL, move_payload(other_tenant, category))

    copy = Song.objects.exclude(pk=song.pk).get(name=song.name)
    assert copy.text == song.text
    assert copy.capo == song.capo


def test_moving_several_categories_at_once(superuser_client, category, make_category, tenant, other_tenant):
    """Every selected category is handed over"""
    second = make_category(tenant, name="Second", slug="second")

    superuser_client.post(MOVE_URL, move_payload(other_tenant, category, second))

    category.refresh_from_db()
    second.refresh_from_db()
    assert category.tenant == other_tenant
    assert second.tenant == other_tenant
