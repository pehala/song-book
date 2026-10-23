"""Tests for the generated files pages."""

import json

import pytest
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils.timezone import now

from pdf.models import Status
from pdf.models.request import PDFFile
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db


def menu_cache_key(tenant):
    return tenant_cache_key(tenant, settings.PDF_CACHE_KEY)


def prime_menu_cache(tenant):
    cache.set(menu_cache_key(tenant), ["stale"], 60)


@pytest.fixture
def finished_file(tenant, category):
    file = PDFFile.objects.create(
        tenant=tenant,
        template=category,
        filename="songbook",
        status=Status.DONE,
        update_date=now(),
        progress=7,
    )
    file.file.save("songbook.pdf", ContentFile(b"%PDF-"))
    return file


def test_list_shows_files_of_this_tenant_only(staff_client, pdf_file, other_tenant):
    """The file list is scoped to the tenant being served"""
    foreign = PDFFile.objects.create(tenant=other_tenant, filename="foreign", update_date=now())

    listed = staff_client.get(reverse("pdf:files:list")).context["files"]

    assert pdf_file in listed
    assert foreign not in listed


def test_delete_removes_the_file(staff_client, pdf_file):
    """Confirming the deletion removes the record"""
    response = staff_client.post(reverse("pdf:files:delete", kwargs={"pk": pdf_file.pk}))

    assert response.status_code == 302
    assert not PDFFile.objects.filter(pk=pdf_file.pk).exists()


def test_delete_drops_the_files_menu_cache(staff_client, tenant, pdf_file):
    """A removed file has to disappear from the navigation"""
    prime_menu_cache(tenant)

    staff_client.post(reverse("pdf:files:delete", kwargs={"pk": pdf_file.pk}))

    assert cache.get(menu_cache_key(tenant)) is None


def test_edit_changes_the_display_name(staff_client, pdf_file):
    """The display name can be changed after generation"""
    staff_client.post(
        reverse("pdf:files:edit", kwargs={"pk": pdf_file.pk}),
        {"display_name": "Campfire", "public": True, "filename": pdf_file.filename},
    )

    pdf_file.refresh_from_db()
    assert pdf_file.display_name == "Campfire"


def test_edit_drops_the_files_menu_cache(staff_client, tenant, pdf_file):
    """A renamed file has to show up in the navigation"""
    prime_menu_cache(tenant)

    staff_client.post(
        reverse("pdf:files:edit", kwargs={"pk": pdf_file.pk}),
        {"display_name": "Campfire", "public": True, "filename": pdf_file.filename},
    )

    assert cache.get(menu_cache_key(tenant)) is None


def test_filename_cannot_be_changed(staff_client, pdf_file):
    """The filename belongs to the template and stays read only"""
    response = staff_client.get(reverse("pdf:files:edit", kwargs={"pk": pdf_file.pk}))

    assert response.context["form"].fields["filename"].disabled


def test_wait_page_shows_the_file(anon_client, pdf_file):
    """The waiting page is about the file being generated"""
    response = anon_client.get(reverse("pdf:files:wait", kwargs={"pk": pdf_file.pk}))

    assert response.context["pdf"] == pdf_file


def test_info_reports_a_pending_file(anon_client, pdf_file):
    """An unfinished file has no download link yet"""
    response = anon_client.get(reverse("pdf:files:info", kwargs={"pk": pdf_file.pk}))

    data = json.loads(response.content)
    assert data["ready"] is False
    assert data["link"] is None


def test_info_reports_a_finished_file(anon_client, finished_file):
    """A finished file is reported with its download link"""
    response = anon_client.get(reverse("pdf:files:info", kwargs={"pk": finished_file.pk}))

    data = json.loads(response.content)
    assert data["ready"] is True
    assert data["link"] == finished_file.file.url
    assert data["progress"] == 7


def test_template_edit_redirects_to_the_category(staff_client, pdf_file, category):
    """Files generated from a category lead back to the category form"""
    response = staff_client.get(reverse("pdf:files:template_edit", kwargs={"pk": pdf_file.pk}))

    assert response.status_code == 302
    assert response["Location"] == reverse("category:edit", kwargs={"pk": category.pk})


def test_template_edit_redirects_to_the_manual_template(staff_client, tenant, manual_template):
    """Files generated from a manual template lead back to the template form"""
    file = PDFFile.objects.create(tenant=tenant, template=manual_template, filename="manual", update_date=now())

    response = staff_client.get(reverse("pdf:files:template_edit", kwargs={"pk": file.pk}))

    assert response.status_code == 302
    assert response["Location"] == reverse("pdf:templates:edit", kwargs={"pk": manual_template.pk})


def test_template_edit_without_a_template(staff_client, tenant):
    """A file whose template is gone answers with a 404

    The template FK is SET_NULL, so orphaned files happen whenever a category or
    manual template is deleted.
    """
    file = PDFFile.objects.create(tenant=tenant, filename="orphan", update_date=now())

    response = staff_client.get(reverse("pdf:files:template_edit", kwargs={"pk": file.pk}))

    assert response.status_code == 404
