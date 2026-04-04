"""PDF-specific pytest fixtures.

These fixtures are scoped to tests/pdf/ and do not affect other test modules.
"""

import pytest
from unittest.mock import patch, MagicMock

from django.utils.timezone import now

from backend.models import Song
from category.models import Category
from pdf.models import Status
from pdf.models.request import PDFFile, ManualPDFTemplate, PDFSong


@pytest.fixture
def pdf_category(tenant):
    """A Category with generate_pdf=True, suitable for triggering PDF generation."""
    return Category.objects.create(
        tenant=tenant,
        name="PDF Category",
        slug="pdf-cat",
        generate_pdf=True,
        filename="test-cat",
        locale="en",
    )


@pytest.fixture
def pdf_song(pdf_category):
    """A non-archived song in pdf_category."""
    s = Song.objects.create(name="PDF Song", text="{Am}Hello {C}World")
    s.categories.add(pdf_category)
    return s


@pytest.fixture
def archived_pdf_song(pdf_category):
    """An archived song in pdf_category — should be excluded from PDF."""
    s = Song.objects.create(name="Archived PDF Song", text="x", archived=True)
    s.categories.add(pdf_category)
    return s


@pytest.fixture
def manual_template(tenant):
    """A ManualPDFTemplate linked to tenant."""
    return ManualPDFTemplate.objects.create(
        tenant=tenant,
        name="Manual Template",
        filename="manual",
        locale="en",
    )


@pytest.fixture
def pdf_song_entry(manual_template, pdf_song):
    """A PDFSong linking pdf_song into manual_template at song_number=1."""
    return PDFSong.objects.create(
        song=pdf_song,
        request=manual_template,
        song_number=1,
    )


@pytest.fixture
def make_scheduled_file(tenant):
    """Factory fixture: create a SCHEDULED PDFFile for any template.

    Usage::

        def test_foo(make_scheduled_file, pdf_category):
            file = make_scheduled_file(pdf_category)
    """

    def _factory(template):
        return PDFFile.objects.create(
            template=template,
            tenant=tenant,
            filename=template.filename,
            status=Status.SCHEDULED,
            update_date=now(),
            scheduled_at=now(),
            public=True,
        )

    return _factory


@pytest.fixture
def mock_weasyprint():
    """Patches pdf.generate.weasyprint.HTML so no real PDF rendering occurs.

    The mock's write_pdf() writes b"%PDF-fake" to the output file handle,
    producing a recognisable but minimal stand-in for a real PDF.
    """

    def fake_write_pdf(target, **kwargs):
        target.write(b"%PDF-fake")

    mock_html_instance = MagicMock()
    mock_html_instance.write_pdf.side_effect = fake_write_pdf

    with patch("pdf.generate.weasyprint.HTML", return_value=mock_html_instance) as mock_cls:
        yield mock_cls
