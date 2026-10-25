"""PDF-specific pytest fixtures.

These fixtures are scoped to tests/pdf/ and do not affect other test modules.
"""

from unittest.mock import MagicMock, patch

import pytest

from pdf.models.request import PDFSong


@pytest.fixture
def pdf_category(tenant, make_category):
    """A Category with generate_pdf=True, suitable for triggering PDF generation."""
    return make_category(tenant, name="PDF Category", slug="pdf-cat", generate_pdf=True, filename="test-cat")


@pytest.fixture
def pdf_song(pdf_category, make_song):
    """A non-archived song in pdf_category."""
    return make_song(pdf_category, name="PDF Song", text="{Am}Hello {C}World")


@pytest.fixture
def pdf_song_entry(manual_template, pdf_song):
    """A PDFSong linking pdf_song into manual_template at song_number=1."""
    return PDFSong.objects.create(song=pdf_song, request=manual_template, song_number=1)


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
