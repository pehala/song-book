"""Tests for the generated files pages."""

import json

import pytest
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

from pdf.models import Status
from pdf.models.request import PDFFile
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db


def menu_cache_key(tenant):
    """The cache key of the PDF menu of the tenant."""
    return tenant_cache_key(tenant, settings.PDF_CACHE_KEY)


def prime_menu_cache(tenant):
    """Puts a stale entry into the tenant's PDF menu cache."""
    cache.set(menu_cache_key(tenant), ["stale"], 60)


@pytest.fixture
def finished_file(category, make_pdf_file):
    """A finished PDF file of the category."""
    return make_pdf_file(category, status=Status.DONE, progress=7, content=b"%PDF-")


def test_list_shows_files_of_this_tenant_only(staff_client, pdf_file, other_tenant, make_pdf_file):
    """The file list is scoped to the tenant being served."""
    foreign = make_pdf_file(tenant=other_tenant)

    listed = staff_client.get(reverse("pdf:files:list")).context["files"]

    assert pdf_file in listed
    assert foreign not in listed


def test_delete_removes_the_file(staff_client, tenant, pdf_file):
    """Confirming the deletion removes the record and drops the files menu, where it has to disappear from."""
    prime_menu_cache(tenant)

    response = staff_client.post(reverse("pdf:files:delete", kwargs={"pk": pdf_file.pk}))

    assert response.status_code == 302
    assert not PDFFile.objects.filter(pk=pdf_file.pk).exists()
    assert cache.get(menu_cache_key(tenant)) is None


def test_edit_changes_the_display_name(staff_client, tenant, pdf_file):
    """The display name can be changed after generation, which the files menu has to show."""
    prime_menu_cache(tenant)

    staff_client.post(
        reverse("pdf:files:edit", kwargs={"pk": pdf_file.pk}),
        {"display_name": "Campfire", "public": True, "filename": pdf_file.filename},
    )

    pdf_file.refresh_from_db()
    assert pdf_file.display_name == "Campfire"
    assert cache.get(menu_cache_key(tenant)) is None


def test_filename_cannot_be_changed(staff_client, pdf_file):
    """The filename belongs to the template and stays read only."""
    response = staff_client.get(reverse("pdf:files:edit", kwargs={"pk": pdf_file.pk}))

    assert response.context["form"].fields["filename"].disabled


def test_wait_page_shows_the_file(anon_client, pdf_file):
    """The waiting page is about the file being generated."""
    response = anon_client.get(reverse("pdf:files:wait", kwargs={"pk": pdf_file.pk}))

    assert response.context["pdf"] == pdf_file


def test_wait_page_tells_the_browser_what_to_poll(anon_client, pdf_file):
    """The progress is drawn in the browser from the file's info."""
    response = anon_client.get(reverse("pdf:files:wait", kwargs={"pk": pdf_file.pk}))

    assert response.context["page"] == {
        "filename": pdf_file.filename,
        "info": reverse("pdf:files:info", kwargs={"pk": pdf_file.pk}),
    }
    assert b'<script id="page-data" type="application/json">' in response.content


def test_info_reports_a_pending_file(anon_client, pdf_file):
    """An unfinished file has no download link yet."""
    response = anon_client.get(reverse("pdf:files:info", kwargs={"pk": pdf_file.pk}))

    data = json.loads(response.content)
    assert data["ready"] is False
    assert data["failed"] is False
    assert data["link"] is None


def test_info_reports_a_failed_file(anon_client, pdf_file):
    """A file that failed to render ends the polling."""
    pdf_file.status = Status.FAILED
    pdf_file.save()

    data = json.loads(anon_client.get(reverse("pdf:files:info", kwargs={"pk": pdf_file.pk})).content)

    assert data["failed"] is True
    assert data["ready"] is False


def test_info_reports_a_finished_file(anon_client, finished_file):
    """A finished file is reported with its download link."""
    response = anon_client.get(reverse("pdf:files:info", kwargs={"pk": finished_file.pk}))

    data = json.loads(response.content)
    assert data["ready"] is True
    assert data["link"] == finished_file.file.url
    assert data["progress"] == 7


@pytest.mark.parametrize(
    ("template_fixture", "edit_view"),
    [
        pytest.param("category", "category:edit", id="category"),
        pytest.param("manual_template", "pdf:templates:edit", id="manual template"),
    ],
)
def test_template_edit_redirects_to_the_form_of_the_template(
    request, staff_client, make_pdf_file, template_fixture, edit_view
):
    """A file leads back to the form of the template it was generated from."""
    template = request.getfixturevalue(template_fixture)
    file = make_pdf_file(template)

    response = staff_client.get(reverse("pdf:files:template_edit", kwargs={"pk": file.pk}))

    assert response.status_code == 302
    assert response["Location"] == reverse(edit_view, kwargs={"pk": template.pk})


def test_template_edit_redirects_to_the_all_songs_form(staff_client, all_songs_template, make_pdf_file):
    """Files generated from the all songs template lead back to its form."""
    file = make_pdf_file(all_songs_template)

    response = staff_client.get(reverse("pdf:files:template_edit", kwargs={"pk": file.pk}))

    assert response.status_code == 302
    assert response["Location"] == reverse("category:edit_all")


def test_template_edit_without_a_template(staff_client, make_pdf_file):
    """A file whose template is gone answers with a 404.

    The template FK is SET_NULL, so orphaned files happen whenever a category or
    manual template is deleted.
    """
    file = make_pdf_file()

    response = staff_client.get(reverse("pdf:files:template_edit", kwargs={"pk": file.pk}))

    assert response.status_code == 404


@pytest.fixture
def foreign_file(other_category, make_pdf_file):
    """A file of another tenant."""
    return make_pdf_file(other_category)


def test_template_of_a_file_of_another_tenant_is_not_found(staff_client, foreign_file):
    """A local admin cannot reach the template of a file of another tenant."""
    response = staff_client.get(reverse("pdf:files:template_edit", kwargs={"pk": foreign_file.pk}))

    assert response.status_code == 404


def test_file_of_another_tenant_cannot_be_deleted(staff_client, foreign_file):
    """Confirming the deletion of a foreign file leaves it in place."""
    response = staff_client.post(reverse("pdf:files:delete", kwargs={"pk": foreign_file.pk}))

    assert response.status_code == 404
    assert PDFFile.objects.filter(pk=foreign_file.pk).exists()


def test_file_of_another_tenant_cannot_be_edited(staff_client, foreign_file):
    """Saving the edit form of a foreign file changes nothing."""
    response = staff_client.post(
        reverse("pdf:files:edit", kwargs={"pk": foreign_file.pk}), {"display_name": "Renamed", "public": "on"}
    )

    assert response.status_code == 404
    foreign_file.refresh_from_db()
    assert foreign_file.display_name is None


@pytest.mark.parametrize("name", ["pdf:files:wait", "pdf:files:info"])
def test_progress_of_a_file_of_another_tenant_is_not_found(anon_client, foreign_file, name):
    """The waiting page and its polling endpoint only know files of the tenant being served."""
    response = anon_client.get(reverse(name, kwargs={"pk": foreign_file.pk}))

    assert response.status_code == 404


def test_generate_now_generates_the_file_and_shows_its_progress(staff_client, make_pdf_file, category, mock_weasyprint):
    """Posting to the generate now page generates the scheduled file and leads to its waiting page."""
    file = make_pdf_file(category, status=Status.SCHEDULED)

    response = staff_client.post(reverse("pdf:files:generate_now", kwargs={"pk": file.pk}))

    assert response.status_code == 302
    assert response["Location"] == reverse("pdf:files:wait", kwargs={"pk": file.pk})
    file.refresh_from_db()
    assert file.status == Status.DONE


def test_generate_now_refuses_a_file_that_is_not_scheduled(staff_client, make_pdf_file, category, mock_weasyprint):
    """A file that is already done is left alone and the list is shown again."""
    file = make_pdf_file(category, status=Status.DONE)

    response = staff_client.post(reverse("pdf:files:generate_now", kwargs={"pk": file.pk}))

    assert response["Location"] == reverse("pdf:files:list")
    mock_weasyprint.assert_not_called()


def test_generate_now_needs_a_post(staff_client, make_pdf_file, category):
    """Generating is not started by opening a link."""
    file = make_pdf_file(category, status=Status.SCHEDULED)

    response = staff_client.get(reverse("pdf:files:generate_now", kwargs={"pk": file.pk}))

    assert response.status_code == 405


def test_generate_now_is_for_local_admins(anon_client, plain_client, make_pdf_file, category, mock_weasyprint):
    """Neither visitors nor users without rights can generate a scheduled file now."""
    file = make_pdf_file(category, status=Status.SCHEDULED)
    url = reverse("pdf:files:generate_now", kwargs={"pk": file.pk})

    assert anon_client.post(url).status_code == 302
    assert plain_client.post(url).status_code == 403
    mock_weasyprint.assert_not_called()


def test_generate_now_of_a_file_of_another_tenant_is_not_found(staff_client, foreign_file, mock_weasyprint):
    """A local admin cannot generate the file of another tenant."""
    foreign_file.status = Status.SCHEDULED
    foreign_file.save()

    response = staff_client.post(reverse("pdf:files:generate_now", kwargs={"pk": foreign_file.pk}))

    assert response.status_code == 404
    mock_weasyprint.assert_not_called()


def test_only_scheduled_files_offer_generating_now(staff_client, make_pdf_file, category):
    """The file list offers to generate a scheduled file now, and not a finished one."""
    scheduled = make_pdf_file(category, status=Status.SCHEDULED)
    url = reverse("pdf:files:generate_now", kwargs={"pk": scheduled.pk})

    assert url in staff_client.get(reverse("pdf:files:list")).content.decode()

    PDFFile.objects.filter(pk=scheduled.pk).update(status=Status.DONE)

    assert url not in staff_client.get(reverse("pdf:files:list")).content.decode()
