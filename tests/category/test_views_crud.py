"""Tests for creating, updating and deleting categories."""

import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

from category.models import Category
from pdf.models.request import PDFFile
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db


def category_payload(tenant, **overrides):
    """Valid CategoryForm data"""
    data = {
        "name": "Created Category",
        "slug": "created",
        "tenant": tenant.pk,
        "filename": "songbook",
        "locale": "en",
        "title": "",
        "display_name": "",
        "link": "",
        "generate_pdf": False,
        "public": True,
        "show_date": True,
    }
    data.update(overrides)
    return data


def menu_cache_key(tenant):
    return tenant_cache_key(tenant, settings.CATEGORY_CACHE_KEY)


def prime_menu_cache(tenant):
    """The categories menu is cached per tenant and has to be dropped on change"""
    cache.set(menu_cache_key(tenant), ["stale"], 60)


def test_list_shows_categories_of_this_tenant_only(staff_client, category, other_category):
    """The management list is scoped to the tenant being served"""
    listed = staff_client.get(reverse("category:list")).context["categories"]

    assert category in listed
    assert other_category not in listed


def test_list_counts_active_songs(staff_client, category, song, archived_song):
    """The song count column ignores archived songs"""
    listed = staff_client.get(reverse("category:list")).context["categories"]

    assert next(entry for entry in listed if entry.pk == category.pk).song_count == 1


def test_create_form_is_prefilled_for_the_tenant(staff_client, tenant):
    """The hidden tenant field and the default filename are filled in"""
    initial = staff_client.get(reverse("category:add")).context["form"].initial

    assert initial["tenant"] == tenant
    assert initial["filename"]


def test_create_adds_category(staff_client, tenant):
    """Posting the add form stores a new category"""
    response = staff_client.post(reverse("category:add"), category_payload(tenant))

    assert response.status_code == 302
    assert Category.objects.filter(slug="created", tenant=tenant).exists()


def test_create_drops_the_menu_cache(staff_client, tenant):
    """A new category has to show up in the navigation"""
    prime_menu_cache(tenant)

    staff_client.post(reverse("category:add"), category_payload(tenant))

    assert cache.get(menu_cache_key(tenant)) is None


def test_update_changes_category(staff_client, tenant, category):
    """Posting the edit form stores the new values"""
    url = reverse("category:edit", kwargs={"pk": category.pk})

    staff_client.post(url, category_payload(tenant, name="Renamed", slug=category.slug))

    category.refresh_from_db()
    assert category.name == "Renamed"


def test_update_drops_the_menu_cache(staff_client, tenant, category):
    """A renamed category has to show up in the navigation"""
    prime_menu_cache(tenant)

    staff_client.post(
        reverse("category:edit", kwargs={"pk": category.pk}),
        category_payload(tenant, name="Renamed", slug=category.slug),
    )

    assert cache.get(menu_cache_key(tenant)) is None


def test_update_schedules_pdf_when_enabled(staff_client, tenant, make_category):
    """Changing a printed category queues a fresh PDF"""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)

    staff_client.post(
        reverse("category:edit", kwargs={"pk": category.pk}),
        category_payload(tenant, name="Renamed", slug="printed", generate_pdf=True),
    )

    assert PDFFile.objects.filter(template=category).exists()


def test_update_without_changes_schedules_nothing(staff_client, tenant, make_category):
    """Resubmitting identical data does not queue a PDF"""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)
    unchanged = category_payload(tenant, name="Printed", slug="printed", generate_pdf=True)

    staff_client.post(reverse("category:edit", kwargs={"pk": category.pk}), unchanged)

    assert not PDFFile.objects.filter(template=category).exists()


def test_delete_removes_category(staff_client, category):
    """Confirming the deletion removes the category"""
    response = staff_client.post(reverse("category:delete", kwargs={"pk": category.pk}))

    assert response.status_code == 302
    assert not Category.objects.filter(pk=category.pk).exists()


def test_delete_drops_the_menu_cache(staff_client, tenant, category):
    """A removed category has to disappear from the navigation"""
    prime_menu_cache(tenant)

    staff_client.post(reverse("category:delete", kwargs={"pk": category.pk}))

    assert cache.get(menu_cache_key(tenant)) is None


def test_delete_invalidates_songs_cache(staff_client, anon_client, tenant, category, song):
    """The JSON of the songs that were in the category is evicted"""
    anon_client.get(reverse("chords:all_data"))
    key = tenant_cache_key(tenant, f"{settings.SONGS_CACHE_KEY}_ALL")
    assert cache.get(key) is not None

    staff_client.post(reverse("category:delete", kwargs={"pk": category.pk}))

    assert cache.get(key) is None
