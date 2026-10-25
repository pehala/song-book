"""Tests for creating, updating and deleting categories."""

from datetime import timedelta

import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils.timezone import now

from backend.cache import songs_payload_key
from category.models import Category
from pdf.models import Status
from pdf.models.request import PDFFile
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db


def category_payload(tenant, **overrides):
    """Valid CategoryForm data."""
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
    """The cache key of the categories menu of the tenant."""
    return tenant_cache_key(tenant, settings.CATEGORY_CACHE_KEY)


def prime_menu_cache(tenant):
    """The categories menu is cached per tenant and has to be dropped on change."""
    cache.set(menu_cache_key(tenant), ["stale"], 60)


def test_list_shows_categories_of_this_tenant_only(staff_client, category, other_category):
    """The management list is scoped to the tenant being served."""
    listed = staff_client.get(reverse("category:list")).context["categories"]

    assert category in listed
    assert other_category not in listed


def test_list_links_the_last_generated_file_while_a_newer_one_waits(staff_client, tenant, category):
    """The newest file being scheduled does not replace the link to the last finished one."""
    common = {"tenant": tenant, "template": category, "filename": "songbook"}
    PDFFile.objects.create(status=Status.DONE, file="songbook.pdf", update_date=now() - timedelta(days=1), **common)
    PDFFile.objects.create(status=Status.SCHEDULED, update_date=now(), **common)

    content = staff_client.get(reverse("category:list")).content.decode()

    assert 'target="_blank">songbook.pdf</a>' in content


def test_list_counts_active_songs(staff_client, category, song, archived_song):
    """The song count column ignores archived songs."""
    listed = staff_client.get(reverse("category:list")).context["categories"]

    assert next(entry for entry in listed if entry.pk == category.pk).song_count == 1


def test_create_form_is_prefilled_for_the_tenant(staff_client, tenant):
    """The hidden tenant field and the default filename are filled in."""
    initial = staff_client.get(reverse("category:add")).context["form"].initial

    assert initial["tenant"] == tenant
    assert initial["filename"]


def test_create_adds_category(staff_client, tenant):
    """Posting the add form stores a new category."""
    response = staff_client.post(reverse("category:add"), category_payload(tenant))

    assert response.status_code == 302
    assert Category.objects.filter(slug="created", tenant=tenant).exists()


def test_create_schedules_the_all_songs_pdf(staff_client, tenant, all_songs_template):
    """A new category is a section of the all songs PDF."""
    staff_client.post(reverse("category:add"), category_payload(tenant))

    assert PDFFile.objects.filter(template=all_songs_template).count() == 1


def test_create_drops_the_menu_cache(staff_client, tenant):
    """A new category has to show up in the navigation."""
    prime_menu_cache(tenant)

    staff_client.post(reverse("category:add"), category_payload(tenant))

    assert cache.get(menu_cache_key(tenant)) is None


def test_update_changes_category(staff_client, tenant, category):
    """Posting the edit form stores the new values."""
    url = reverse("category:edit", kwargs={"pk": category.pk})

    staff_client.post(url, category_payload(tenant, name="Renamed", slug=category.slug))

    category.refresh_from_db()
    assert category.name == "Renamed"


def test_update_drops_the_menu_cache(staff_client, tenant, category):
    """A renamed category has to show up in the navigation."""
    prime_menu_cache(tenant)

    staff_client.post(
        reverse("category:edit", kwargs={"pk": category.pk}),
        category_payload(tenant, name="Renamed", slug=category.slug),
    )

    assert cache.get(menu_cache_key(tenant)) is None


def test_update_schedules_pdf_when_enabled(staff_client, tenant, make_category):
    """Changing a printed category queues a fresh PDF."""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)

    staff_client.post(
        reverse("category:edit", kwargs={"pk": category.pk}),
        category_payload(tenant, name="Renamed", slug="printed", generate_pdf=True),
    )

    assert PDFFile.objects.filter(template=category).exists()


def test_update_schedules_the_all_songs_pdf(staff_client, tenant, category, all_songs_template):
    """The section titles of the all songs PDF are the category names, so a changed category queues a fresh PDF."""
    staff_client.post(
        reverse("category:edit", kwargs={"pk": category.pk}),
        category_payload(tenant, name="Renamed", slug=category.slug),
    )

    assert PDFFile.objects.filter(template=all_songs_template).count() == 1


def test_update_without_changes_schedules_no_all_songs_pdf(staff_client, tenant, category, all_songs_template):
    """Resubmitting identical data does not queue the all songs PDF."""
    unchanged = category_payload(
        tenant, name=category.name, slug=category.slug, filename=category.filename, locale=category.locale
    )

    staff_client.post(reverse("category:edit", kwargs={"pk": category.pk}), unchanged)

    assert not PDFFile.objects.filter(template=all_songs_template).exists()


def test_update_without_changes_schedules_nothing(staff_client, tenant, make_category):
    """Resubmitting identical data does not queue a PDF."""
    category = make_category(tenant, name="Printed", slug="printed", generate_pdf=True)
    unchanged = category_payload(tenant, name="Printed", slug="printed", generate_pdf=True)

    staff_client.post(reverse("category:edit", kwargs={"pk": category.pk}), unchanged)

    assert not PDFFile.objects.filter(template=category).exists()


def test_delete_removes_category(staff_client, category):
    """Confirming the deletion removes the category."""
    response = staff_client.post(reverse("category:delete", kwargs={"pk": category.pk}))

    assert response.status_code == 302
    assert not Category.objects.filter(pk=category.pk).exists()


def test_delete_schedules_the_all_songs_pdf(staff_client, category, all_songs_template):
    """A deleted category is no longer a section of the all songs PDF."""
    staff_client.post(reverse("category:delete", kwargs={"pk": category.pk}))

    assert PDFFile.objects.filter(template=all_songs_template).count() == 1


def test_delete_drops_the_menu_cache(staff_client, tenant, category):
    """A removed category has to disappear from the navigation."""
    prime_menu_cache(tenant)

    staff_client.post(reverse("category:delete", kwargs={"pk": category.pk}))

    assert cache.get(menu_cache_key(tenant)) is None


def test_delete_invalidates_songs_cache(staff_client, anon_client, tenant, category, song):
    """The payload of the songs that were in the category is evicted."""
    anon_client.get(reverse("chords:songs_api"))
    key = songs_payload_key(tenant, False)
    assert cache.get(key) is not None

    staff_client.post(reverse("category:delete", kwargs={"pk": category.pk}))

    assert cache.get(key) is None


@pytest.mark.parametrize("name", ["category:edit", "category:delete"])
def test_pages_of_a_category_of_another_tenant_are_not_found(staff_client, other_category, name):
    """A local admin cannot reach categories of another tenant."""
    response = staff_client.get(reverse(name, kwargs={"pk": other_category.pk}))

    assert response.status_code == 404


def test_category_of_another_tenant_cannot_be_updated(staff_client, other_tenant, other_category):
    """Saving the edit form of a foreign category changes nothing."""
    url = reverse("category:edit", kwargs={"pk": other_category.pk})

    response = staff_client.post(url, category_payload(other_tenant, name="Renamed", slug=other_category.slug))

    assert response.status_code == 404
    other_category.refresh_from_db()
    assert other_category.name == "Other Category"


def test_category_of_another_tenant_cannot_be_deleted(staff_client, other_category):
    """Confirming the deletion of a foreign category leaves it in place."""
    response = staff_client.post(reverse("category:delete", kwargs={"pk": other_category.pk}))

    assert response.status_code == 404
    assert Category.objects.filter(pk=other_category.pk).exists()


def test_category_cannot_be_created_in_another_tenant(staff_client, other_tenant):
    """The hidden tenant field only accepts the tenant being served."""
    response = staff_client.post(reverse("category:add"), category_payload(other_tenant))

    assert response.status_code == 200
    assert "tenant" in response.context["form"].errors
    assert not Category.objects.filter(name="Created Category").exists()


def test_category_cannot_be_moved_to_another_tenant(staff_client, tenant, other_tenant, category):
    """Editing a category cannot hand it over to another tenant."""
    url = reverse("category:edit", kwargs={"pk": category.pk})

    staff_client.post(url, category_payload(other_tenant, name="Renamed", slug=category.slug))

    category.refresh_from_db()
    assert category.tenant == tenant
    assert category.name != "Renamed"
