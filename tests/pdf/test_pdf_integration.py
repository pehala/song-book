"""Integration test for the full WeasyPrint PDF rendering path.

This test calls generate_pdf() with NO mocking of WeasyPrint itself.
It exercises the complete pipeline: Django template rendering → WeasyPrint
HTML parsing → PDF byte stream → FileField save.

The test is intentionally slow (real PDF rendering) and is isolated in its
own module so it can be skipped in fast-feedback CI runs with:

    pytest -m "not slow"

Requires that static files (pdf.css, OpenSans fonts) are present on disk,
which they are as part of the source tree (pdf/static/).
"""

import pytest

from pdf.generate import generate_pdf
from pdf.models import Status

pytestmark = [pytest.mark.django_db, pytest.mark.slow]


def test_full_pdf_generation_produces_valid_pdf_bytes(pdf_category, pdf_song, make_scheduled_file):
    """End-to-end: generate_pdf() produces a real PDF file starting with %PDF.

    No WeasyPrint mocking. Verifies:
    - status transitions to DONE
    - a file is written to the filesystem
    - the file starts with the standard PDF header b"%PDF"
    - the output is non-trivial (> 1 kB)
    """
    pdf_file = make_scheduled_file(pdf_category)

    success, duration = generate_pdf(pdf_file, pdf_category)

    pdf_file.refresh_from_db()

    assert success is True, "generate_pdf() returned False; check logs for errors"
    assert pdf_file.status == Status.DONE
    assert pdf_file.file, "PDFFile.file should be set after successful generation"
    assert pdf_file.file.name.endswith(".pdf")

    # Read the first bytes from the generated file to verify it is a real PDF
    with pdf_file.file.open("rb") as fh:
        header = fh.read(4)
    assert header == b"%PDF", f"File does not start with PDF header; got {header!r}"

    # Sanity-check that the output is non-trivially sized
    assert pdf_file.file.size > 1024, f"Generated PDF is suspiciously small: {pdf_file.file.size} bytes"

    # Clean up the generated file so it does not accumulate between test runs
    pdf_file.file.delete(save=False)
