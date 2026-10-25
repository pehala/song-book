"""Tests for PDF generation and scheduling."""

import logging

import pytest
from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now

from pdf.generate import (
    ProgressFilter,
    Timer,
    generate_file_now,
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
    """A category that is ready to be printed."""
    category.title = "Campfire Songbook"
    category.save()
    return category


def test_scheduling_creates_a_file_for_the_template(category, mock_weasyprint):
    """The file records which tenant and template it came from."""
    file = generate_pdf_file(category)

    assert file.tenant == category.tenant
    assert file.filename == category.filename


def test_a_delayed_request_waits_to_be_rendered(category):
    """A file queued for later is left alone until its time comes."""
    file = generate_pdf_file(category, delay=600)

    file.refresh_from_db()
    assert file.status == Status.SCHEDULED


def test_scheduling_honours_the_delay(category):
    """A delayed request is scheduled into the future."""
    file = generate_pdf_file(category, delay=600)

    assert (file.scheduled_at - now()).total_seconds() > 300


def test_scheduling_copies_visibility(make_category, tenant):
    """A private template produces a private file."""
    category = make_category(tenant, name="Private", slug="private", public=False)

    assert generate_pdf_file(category).public is False


@pytest.mark.slow
def test_generating_writes_a_pdf(printable):
    """Rendering a category produces a real PDF file."""
    file = generate_pdf_file(printable)

    success, duration = generate_pdf(file, printable)

    file.refresh_from_db()
    assert success
    assert duration > 0
    assert file.status == Status.DONE
    assert file.file.read().startswith(b"%PDF")


@pytest.mark.slow
def test_the_background_task_renders_the_pdf(printable):
    """Running the queued job produces the file the worker was asked for."""
    file = generate_pdf_file(printable, delay=600)

    generate_pdf_job.call_local(file, printable)

    file.refresh_from_db()
    assert file.status == Status.DONE
    assert file.file.read().startswith(b"%PDF")


@pytest.mark.slow
def test_generating_records_how_long_it_took(printable):
    """The elapsed time is stored with the file."""
    file = generate_pdf_file(printable)

    generate_pdf(file, printable)

    file.refresh_from_db()
    assert file.time_elapsed >= 0


@pytest.mark.slow
def test_generating_drops_the_files_menu_cache(printable, tenant):
    """A finished PDF has to appear in the navigation."""
    key = tenant_cache_key(tenant, settings.PDF_CACHE_KEY)
    cache.set(key, ["stale"], 60)
    file = generate_pdf_file(printable)

    generate_pdf(file, printable)

    assert cache.get(key) is None


def test_failed_generation_is_recorded(printable, monkeypatch):
    """A rendering error leaves the file marked as failed."""

    def explode(*args, **kwargs):
        raise RuntimeError("rendering is broken")

    monkeypatch.setattr("pdf.generate.render_to_string", explode)
    file = generate_pdf_file(printable)

    success, _ = generate_pdf(file, printable)

    file.refresh_from_db()
    assert not success
    assert file.status == Status.FAILED


def test_base_url_comes_from_the_settings(settings):
    """A configured base url is used to resolve static files."""
    settings.WEASYPRINT_BASEURL = "/custom/"

    assert get_base_url() == "/custom/"


def test_base_url_falls_back_to_the_index(settings):
    """Without configuration the site root is used."""
    del settings.WEASYPRINT_BASEURL

    assert get_base_url() == "/"


def test_timer_measures_the_block():
    """The timer reports a non negative duration."""
    timer = Timer()

    with timer:
        pass

    assert timer.duration >= 0


def record(message):
    """Returns a log record with the given message."""
    return logging.LogRecord("test", logging.INFO, __file__, 1, message, None, None)


def test_progress_filter_stores_the_step(tenant):
    """Weasyprint progress messages are mirrored onto the file."""
    file = PDFFile.objects.create(tenant=tenant, filename="songbook", update_date=now())

    assert ProgressFilter(file).filter(record("Step 4 - Creating formatting structure"))

    file.refresh_from_db()
    assert file.progress == 4


def test_progress_filter_skips_repeated_steps(tenant):
    """The same step is not written to the database twice."""
    file = PDFFile.objects.create(tenant=tenant, filename="songbook", update_date=now())
    log_filter = ProgressFilter(file)
    log_filter.filter(record("Step 2 - Fetching and parsing CSS"))

    file.progress = 99
    log_filter.file.progress = "2"
    log_filter.filter(record("Step 2 - Fetching and parsing CSS"))

    file.refresh_from_db()
    assert file.progress == 2


def test_generating_now_runs_a_scheduled_file(category, mock_weasyprint):
    """A file waiting for its time is generated at once."""
    file = generate_pdf_file(category, delay=600)

    assert generate_file_now(file)

    file.refresh_from_db()
    assert file.status == Status.DONE
    assert (now() - file.scheduled_at).total_seconds() < 60


@pytest.mark.parametrize("status", [Status.IN_PROGRESS, Status.DONE, Status.FAILED])
def test_a_file_that_is_not_scheduled_is_not_generated_now(category, mock_weasyprint, status):
    """Only a scheduled file can be generated now."""
    file = generate_pdf_file(category, delay=600)
    PDFFile.objects.filter(pk=file.pk).update(status=status)
    file.refresh_from_db()

    assert not generate_file_now(file)

    mock_weasyprint.assert_not_called()
    file.refresh_from_db()
    assert file.status == status


def test_a_file_without_a_template_is_not_generated_now(category, mock_weasyprint):
    """A file whose template was deleted cannot be generated."""
    file = generate_pdf_file(category, delay=600)
    PDFFile.objects.filter(pk=file.pk).update(template=None)
    file.refresh_from_db()

    assert not generate_file_now(file)

    mock_weasyprint.assert_not_called()


def test_the_original_job_leaves_a_file_that_was_generated_now(category, mock_weasyprint):
    """The job still due at the original time does not generate the file a second time."""
    file = generate_pdf_file(category, delay=600)
    generate_file_now(file)

    generate_pdf_job.call_local(file, category)

    assert mock_weasyprint.call_count == 1


def test_a_job_leaves_a_deleted_file(category, mock_weasyprint):
    """A file deleted while it waited is neither generated nor brought back."""
    file = generate_pdf_file(category, delay=600)
    file.delete()

    generate_pdf_job.call_local(file, category)

    mock_weasyprint.assert_not_called()
    assert not PDFFile.objects.filter(pk=file.pk).exists()
