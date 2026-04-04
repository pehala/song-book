"""Unit tests for the PDF generation pipeline.

WeasyPrint is mocked throughout this module — no real PDF rendering occurs.
Tests cover scheduling, status transitions, output correctness, and model
correctness.  Tests for distinct_requests() live in test_distinct_requests.py.
"""

from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

import pytest
from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now

from pdf.generate import generate_pdf, generate_pdf_file, generate_pdf_job
from pdf.models import Status
from pdf.models.request import PDFFile
from tenants.utils import tenant_cache_key

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Group 1 — generate_pdf_file() scheduling
# ---------------------------------------------------------------------------


def test_creates_exactly_one_pdffile_row(mock_weasyprint, pdf_category):
    """generate_pdf_file() creates exactly one PDFFile row for the template.

    With HUEY immediate=True the task runs synchronously, so by the time
    generate_pdf_file() returns the status has already advanced beyond
    SCHEDULED to DONE (or FAILED).
    """
    generate_pdf_file(pdf_category)
    qs = PDFFile.objects.filter(template=pdf_category)
    assert qs.exists()
    assert qs.count() == 1


def test_sets_correct_tenant(mock_weasyprint, pdf_category, tenant):
    """PDFFile is associated with the template's tenant."""
    file = generate_pdf_file(pdf_category)
    assert file.tenant == tenant


def test_sets_scheduled_at_close_to_now(mock_weasyprint, pdf_category):
    """scheduled_at is within 2 seconds of now() when delay=0."""
    before = now()
    file = generate_pdf_file(pdf_category, delay=0)
    after = now()
    assert before <= file.scheduled_at <= after


def test_delay_offsets_scheduled_at(mock_weasyprint, pdf_category):
    """scheduled_at is approximately now() + delay seconds."""
    delay = 60
    before = now()
    file = generate_pdf_file(pdf_category, delay=delay)
    after = now()
    assert before + timedelta(seconds=delay) <= file.scheduled_at <= after + timedelta(seconds=delay)


def test_returns_pdffile_instance(mock_weasyprint, pdf_category):
    """generate_pdf_file() returns the created PDFFile instance."""
    file = generate_pdf_file(pdf_category)
    assert isinstance(file, PDFFile)


# ---------------------------------------------------------------------------
# Group 2 — generate_pdf() status lifecycle
# ---------------------------------------------------------------------------


def test_success_sets_status_and_returns_true(mock_weasyprint, pdf_category, pdf_song, make_scheduled_file):
    """generate_pdf() sets status to DONE and returns (True, duration>=0) on success."""
    file = make_scheduled_file(pdf_category)
    success, duration = generate_pdf(file, pdf_category)
    file.refresh_from_db()
    assert file.status == Status.DONE
    assert success is True
    assert duration >= 0


def test_error_sets_status_and_returns_false(pdf_category, pdf_song, make_scheduled_file):
    """generate_pdf() sets status to FAILED and returns (False, _) when WeasyPrint raises."""
    mock_instance = MagicMock()
    mock_instance.write_pdf.side_effect = RuntimeError("rendering failed")

    file = make_scheduled_file(pdf_category)
    with patch("pdf.generate.weasyprint.HTML", return_value=mock_instance):
        success, _ = generate_pdf(file, pdf_category)

    file.refresh_from_db()
    assert file.status == Status.FAILED
    assert success is False


@pytest.mark.parametrize("weasyprint_raises", [pytest.param(False, id="success"), pytest.param(True, id="error")])
def test_html_tempfile_deleted(pdf_category, pdf_song, make_scheduled_file, weasyprint_raises):
    """The HTML temp file is deleted whether WeasyPrint succeeds or raises."""
    created = []
    original_ntf = tempfile.NamedTemporaryFile

    def tracking_ntf(*args, **kwargs):
        ctx = original_ntf(*args, **kwargs)
        created.append(ctx.name)
        return ctx

    mock_instance = MagicMock()
    if weasyprint_raises:
        mock_instance.write_pdf.side_effect = RuntimeError("rendering failed")
    else:
        mock_instance.write_pdf.side_effect = lambda target, **kw: target.write(b"%PDF-fake")

    file = make_scheduled_file(pdf_category)
    with (
        patch("pdf.generate.tempfile.NamedTemporaryFile", side_effect=tracking_ntf),
        patch("pdf.generate.weasyprint.HTML", return_value=mock_instance),
    ):
        generate_pdf(file, pdf_category)

    assert created, "NamedTemporaryFile was never called"
    assert not Path(created[0]).exists(), "HTML temp file was not deleted"


# ---------------------------------------------------------------------------
# Group 3 — generate_pdf() output correctness
# ---------------------------------------------------------------------------


def test_output_fields_set_after_generation(mock_weasyprint, pdf_category, pdf_song, make_scheduled_file):
    """After a successful run PDFFile.file, time_elapsed, and update_date are all populated."""
    file = make_scheduled_file(pdf_category)
    generate_pdf(file, pdf_category)
    file.refresh_from_db()
    assert file.file
    assert file.file.name.endswith(".pdf")
    assert file.time_elapsed is not None
    assert file.time_elapsed >= 0
    assert file.update_date is not None


def test_pdf_cache_invalidated(mock_weasyprint, pdf_category, pdf_song, tenant, make_scheduled_file):
    """generate_pdf() deletes the PDF menu cache key after a successful run."""
    key = tenant_cache_key(tenant, settings.PDF_CACHE_KEY)
    cache.set(key, "stale-value", timeout=60)

    file = make_scheduled_file(pdf_category)
    generate_pdf(file, pdf_category)

    assert cache.get(key) is None


def test_generate_pdf_for_manual_template(mock_weasyprint, manual_template, pdf_song_entry, make_scheduled_file):
    """generate_pdf() works correctly with a ManualPDFTemplate."""
    file = make_scheduled_file(manual_template)
    success, _ = generate_pdf(file, manual_template)
    file.refresh_from_db()
    assert success is True
    assert file.status == Status.DONE


# ---------------------------------------------------------------------------
# Group 4 — generate_pdf_job Huey task wrapper
# ---------------------------------------------------------------------------


def test_job_marks_file_done(mock_weasyprint, pdf_category, pdf_song, make_scheduled_file):
    """generate_pdf_job() runs synchronously (HUEY immediate) and marks the file DONE."""
    file = make_scheduled_file(pdf_category)
    # In immediate mode (HUEY = {"immediate": True}) the task runs inline.
    generate_pdf_job(file, pdf_category)
    file.refresh_from_db()
    assert file.status == Status.DONE


# ---------------------------------------------------------------------------
# Group 5 — Category.get_songs() correctness
# ---------------------------------------------------------------------------


def test_category_get_songs(pdf_category, pdf_song, archived_pdf_song):
    """get_songs() returns only active songs, numbered from 1."""
    result = pdf_category.get_songs()
    numbers = [n for n, _ in result]
    songs = [s for _, s in result]
    assert pdf_song in songs
    assert archived_pdf_song not in songs
    assert len(songs) == 1
    assert numbers[0] == 1


def test_category_get_songs_empty_category(pdf_category):
    """An empty category returns an empty list."""
    assert pdf_category.get_songs() == []


# ---------------------------------------------------------------------------
# Group 6 — ManualPDFTemplate.get_songs() correctness
# ---------------------------------------------------------------------------


def test_manual_get_songs(manual_template, pdf_song_entry, pdf_song):
    """get_songs() returns the linked song at the correct song number."""
    result = list(manual_template.get_songs())
    songs = [s for _, s in result]
    assert pdf_song in songs
    assert result[0][0] == pdf_song_entry.song_number


@pytest.mark.parametrize("template_fixture", ["pdf_category", "manual_template"])
def test_get_songs_empty(request, template_fixture):
    """An empty Category or ManualPDFTemplate returns an empty list from get_songs()."""
    template = request.getfixturevalue(template_fixture)
    assert list(template.get_songs()) == []


# ---------------------------------------------------------------------------
# Group 7 — has_scheduled_file() duplication guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(Status.SCHEDULED, id="scheduled"),
        pytest.param(Status.IN_PROGRESS, id="in_progress"),
    ],
)
def test_has_scheduled_file_true(pdf_category, make_scheduled_file, status):
    """Returns True for in-flight statuses (SCHEDULED, IN_PROGRESS)."""
    file = make_scheduled_file(pdf_category)
    file.status = status
    file.save()
    assert pdf_category.has_scheduled_file() is True


@pytest.mark.parametrize(
    "status",
    [
        pytest.param(Status.DONE, id="done"),
        pytest.param(Status.FAILED, id="failed"),
        pytest.param(None, id="no_file"),
    ],
)
def test_has_scheduled_file_false(pdf_category, make_scheduled_file, status):
    """Returns False when no file exists or the latest file is DONE/FAILED."""
    if status is not None:
        file = make_scheduled_file(pdf_category)
        file.status = status
        file.save()
    assert pdf_category.has_scheduled_file() is False
