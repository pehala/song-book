"""PDF-specific pytest fixtures.

These fixtures are scoped to tests/pdf/ and do not affect other test modules.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.utils.timezone import now

from backend.models import Song
from category.models import Category
from pdf.models import Status
from pdf.models.request import ManualPDFTemplate, PDFFile, PDFSong


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
def make_pdf_file(tenant):
    """Factory fixture: create a PDFFile, by default a public SCHEDULED one for ``template``.

    ``template`` may be ``None`` for an orphaned file; ``filename`` then defaults to ``"orphan"``.
    ``file`` sets a stub storage path on the row without touching disk.

    Usage::

        def test_foo(make_pdf_file, pdf_category):
            file = make_pdf_file(pdf_category, status=Status.DONE, file="pdfs/fake/test.pdf")
    """

    def _factory(template, status=Status.SCHEDULED, public=True, file=None, update_date=None):
        created = PDFFile.objects.create(
            template=template,
            tenant=tenant,
            filename=template.filename if template else "orphan",
            status=status,
            update_date=update_date or now(),
            scheduled_at=now(),
            public=public,
        )
        if file:
            PDFFile.objects.filter(pk=created.pk).update(file=file)
            created.refresh_from_db()
        return created

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
