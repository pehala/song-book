"""Tests for PDF generation and scheduling."""

import logging

import pytest
from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now

from pdf.generate import (
    ProgressFilter,
    Timer,
    generate_pdf,
    generate_pdf_file,
    generate_pdf_job,
    get_base_url,
)
from pdf.models import Status
from pdf.models.request import PDFFile
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db


@pytest.fixture
def printable(category, song, archived_song):
    """A category that is ready to be printed"""
    category.title = "Campfire Songbook"
    category.save()
    return category


def test_scheduling_creates_a_file_for_the_template(category, mock_weasyprint):
    """The file records which tenant and template it came from"""
    file = generate_pdf_file(category)

    assert file.tenant == category.tenant
    assert file.filename == category.filename


def test_a_delayed_request_waits_to_be_rendered(category):
    """A file queued for later is left alone until its time comes"""
    file = generate_pdf_file(category, delay=600)

    file.refresh_from_db()
    assert file.status == Status.SCHEDULED


def test_scheduling_honours_the_delay(category):
    """A delayed request is scheduled into the future"""
    file = generate_pdf_file(category, delay=600)

    assert (file.scheduled_at - now()).total_seconds() > 300


def test_scheduling_copies_visibility(make_category, tenant):
    """A private template produces a private file"""
    category = make_category(tenant, name="Private", slug="private", public=False)

    assert generate_pdf_file(category).public is False


@pytest.mark.slow
def test_generating_writes_a_pdf(printable):
    """Rendering a category produces a real PDF file"""
    file = generate_pdf_file(printable)

    success, duration = generate_pdf(file, printable)

    file.refresh_from_db()
    assert success
    assert duration > 0
    assert file.status == Status.DONE
    assert file.file.read().startswith(b"%PDF")


@pytest.mark.slow
def test_the_background_task_renders_the_pdf(printable):
    """Running the queued job produces the file the worker was asked for"""
    file = generate_pdf_file(printable)

    generate_pdf_job.call_local(file, printable)

    file.refresh_from_db()
    assert file.status == Status.DONE


@pytest.mark.slow
def test_generating_records_how_long_it_took(printable):
    """The elapsed time is stored with the file"""
    file = generate_pdf_file(printable)

    generate_pdf(file, printable)

    file.refresh_from_db()
    assert file.time_elapsed >= 0


@pytest.mark.slow
def test_generating_drops_the_files_menu_cache(printable, tenant):
    """A finished PDF has to appear in the navigation"""
    key = tenant_cache_key(tenant, settings.PDF_CACHE_KEY)
    cache.set(key, ["stale"], 60)
    file = generate_pdf_file(printable)

    generate_pdf(file, printable)

    assert cache.get(key) is None


def test_failed_generation_is_recorded(printable, monkeypatch):
    """A rendering error leaves the file marked as failed"""

    def explode(*args, **kwargs):
        raise RuntimeError("rendering is broken")

    monkeypatch.setattr("pdf.generate.render_to_string", explode)
    file = generate_pdf_file(printable)

    success, _ = generate_pdf(file, printable)

    file.refresh_from_db()
    assert not success
    assert file.status == Status.FAILED


def test_base_url_comes_from_the_settings(settings):
    """A configured base url is used to resolve static files"""
    settings.WEASYPRINT_BASEURL = "/custom/"

    assert get_base_url() == "/custom/"


def test_base_url_falls_back_to_the_index(settings):
    """Without configuration the site root is used"""
    del settings.WEASYPRINT_BASEURL

    assert get_base_url() == "/"


def test_timer_measures_the_block():
    """The timer reports a non negative duration"""
    timer = Timer()

    with timer:
        pass

    assert timer.duration >= 0


def record(message):
    return logging.LogRecord("test", logging.INFO, __file__, 1, message, None, None)


def test_progress_filter_stores_the_step(tenant):
    """Weasyprint progress messages are mirrored onto the file"""
    file = PDFFile.objects.create(tenant=tenant, filename="songbook", update_date=now())

    assert ProgressFilter(file).filter(record("Step 4 - Creating formatting structure"))

    file.refresh_from_db()
    assert file.progress == 4


def test_progress_filter_skips_repeated_steps(tenant):
    """The same step is not written to the database twice"""
    file = PDFFile.objects.create(tenant=tenant, filename="songbook", update_date=now())
    log_filter = ProgressFilter(file)
    log_filter.filter(record("Step 2 - Fetching and parsing CSS"))

    file.progress = 99
    log_filter.file.progress = "2"
    log_filter.filter(record("Step 2 - Fetching and parsing CSS"))

    file.refresh_from_db()
    assert file.progress == 2
