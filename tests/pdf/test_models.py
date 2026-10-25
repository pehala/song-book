"""Tests for the PDF template and file models."""

import pytest
from django.utils.timezone import now

from pdf.models import Status
from pdf.models.request import PDFFile, upload_path

pytestmark = pytest.mark.django_db


def make_file(tenant, template=None, **kwargs):
    kwargs.setdefault("filename", "songbook")
    kwargs.setdefault("status", Status.QUEUED)
    kwargs.setdefault("update_date", now())
    return PDFFile.objects.create(tenant=tenant, template=template, **kwargs)


def test_name_falls_back_to_the_filename(tenant):
    """Without a display name the file is named after its filename"""
    assert make_file(tenant).name == "songbook.pdf"


def test_display_name_wins(tenant):
    """A display name replaces the filename entirely"""
    assert make_file(tenant, display_name="Campfire").name == "Campfire"


@pytest.mark.parametrize(
    ("status", "finished"),
    [
        pytest.param(Status.QUEUED, False, id="queued"),
        pytest.param(Status.SCHEDULED, False, id="scheduled"),
        pytest.param(Status.IN_PROGRESS, False, id="in progress"),
        pytest.param(Status.DONE, True, id="done"),
        pytest.param(Status.FAILED, True, id="failed"),
    ],
)
def test_finished_reflects_the_status(tenant, status, finished):
    """Only done and failed files are finished"""
    assert make_file(tenant, status=status).finished is finished


def test_latest_file_is_the_most_recent_one(tenant, category):
    """Templates expose the newest file they produced"""
    make_file(tenant, category, update_date=now())
    newest = make_file(tenant, category, update_date=now())

    assert category.latest_file == newest


def test_latest_file_is_none_without_files(category):
    """A template that never produced anything has no latest file"""
    assert category.latest_file is None


@pytest.mark.parametrize(
    ("status", "scheduled"),
    [
        pytest.param(Status.QUEUED, True, id="queued"),
        pytest.param(Status.SCHEDULED, True, id="scheduled"),
        pytest.param(Status.IN_PROGRESS, True, id="in progress"),
        pytest.param(Status.DONE, False, id="done"),
        pytest.param(Status.FAILED, False, id="failed"),
    ],
)
def test_has_scheduled_file(tenant, category, status, scheduled):
    """A template is busy while its newest file is unfinished"""
    make_file(tenant, category, status=status)

    assert bool(category.has_scheduled_file()) is scheduled


def test_has_no_scheduled_file_without_files(category):
    """A template that never produced anything is not busy"""
    assert not category.has_scheduled_file()


def test_copy_options_takes_over_the_print_settings(category, manual_template):
    """Options are copied between templates without touching identity"""
    manual_template.filename = "other"
    manual_template.title = "Other Title"
    manual_template.margin = 2.5
    manual_template.link = "https://example.test"

    category.copy_options(manual_template)

    assert category.filename == "other"
    assert category.title == "Other Title"
    assert category.margin == 2.5
    assert category.link == "https://example.test"
    assert category.name == "Test Category"


@pytest.mark.parametrize(
    ("link", "url"),
    [
        ("", ""),
        ("jerry.crazycactus.eu", "https://jerry.crazycactus.eu"),
        ("  jerry.crazycactus.eu/songs ", "https://jerry.crazycactus.eu/songs"),
        ("localhost:8000", "https://localhost:8000"),
        ("https://jerry.crazycactus.eu", "https://jerry.crazycactus.eu"),
        ("HTTP://jerry.crazycactus.eu", "HTTP://jerry.crazycactus.eu"),
        ("mailto:jerry@example.test", "mailto:jerry@example.test"),
    ],
)
def test_link_url_adds_the_missing_scheme(category, link, url):
    """A link typed without a scheme gets https://, one that names a scheme is kept"""
    category.link = link

    assert category.link_url == url


def test_manual_template_returns_numbered_songs(manual_template, pdf_song_entry, pdf_song):
    """Manual templates print the songs in the order the user assigned"""
    assert manual_template.get_songs() == [(1, pdf_song)]


def test_upload_path_is_namespaced_by_tenant(tenant):
    """Uploaded files are stored per tenant and day"""
    file = make_file(tenant)

    path = upload_path(file, "songbook.pdf")

    assert path.startswith(f"pdfs/{tenant.id}/")
    assert path.endswith("songbook.pdf")
