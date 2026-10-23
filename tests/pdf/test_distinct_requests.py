"""Tests for distinct_requests() — the PDF nav-menu list helper."""

from datetime import timedelta

import pytest
from django.utils.timezone import now

from pdf.models import Status
from tenants.menu_items import distinct_requests

pytestmark = pytest.mark.django_db

FAKE_PATH = "pdfs/fake/250101/test.pdf"


def test_distinct_requests_empty_when_no_files(tenant, pdf_category):
    """Returns [] when no DONE PDFFiles exist."""
    assert distinct_requests(tenant) == []


@pytest.mark.parametrize(
    "template_fixture",
    [
        pytest.param("pdf_category", id="category"),
        pytest.param("manual_template", id="manual_template"),
    ],
)
def test_distinct_requests_shows_template_file(request, tenant, make_pdf_file, template_fixture):
    """Returns one MenuItem for a template (Category or ManualPDFTemplate) with a public DONE PDFFile."""
    template = request.getfixturevalue(template_fixture)
    make_pdf_file(template, status=Status.DONE, file=FAKE_PATH)
    assert len(distinct_requests(tenant)) == 1


def test_distinct_requests_shows_orphan_public_done_file(tenant, make_pdf_file):
    """Orphaned (template=None) public DONE files appear in the menu."""
    make_pdf_file(None, status=Status.DONE, file=FAKE_PATH)
    assert len(distinct_requests(tenant)) == 1


def test_distinct_requests_hides_private_files(tenant, pdf_category, make_pdf_file):
    """Files with public=False are excluded from the menu."""
    make_pdf_file(pdf_category, status=Status.DONE, public=False, file=FAKE_PATH)
    assert distinct_requests(tenant) == []

    make_pdf_file(None, status=Status.DONE, public=False, file=FAKE_PATH)
    assert distinct_requests(tenant) == []


def test_distinct_requests_hides_non_done_files(tenant, pdf_category, make_pdf_file):
    """SCHEDULED, IN_PROGRESS, and FAILED files are not shown."""
    for status in (Status.SCHEDULED, Status.IN_PROGRESS, Status.FAILED):
        make_pdf_file(pdf_category, status=status)
    assert distinct_requests(tenant) == []


@pytest.mark.parametrize("newer_status", [Status.SCHEDULED, Status.FAILED])
def test_distinct_requests_keeps_older_done_file_while_newer_is_pending(
    tenant, pdf_category, make_pdf_file, newer_status
):
    """A newer non-DONE file does not hide the template's older public DONE file."""
    make_pdf_file(pdf_category, status=Status.DONE, file=FAKE_PATH, update_date=now() - timedelta(hours=1))
    make_pdf_file(pdf_category, status=newer_status)
    assert len(distinct_requests(tenant)) == 1


def test_distinct_requests_shows_only_newest_done_file(tenant, pdf_category, make_pdf_file):
    """Only the newest public DONE file per template is listed."""
    make_pdf_file(pdf_category, status=Status.DONE, file=FAKE_PATH, update_date=now() - timedelta(hours=1))
    make_pdf_file(pdf_category, status=Status.DONE, file=FAKE_PATH)
    assert len(distinct_requests(tenant)) == 1
