"""Tests for distinct_requests() — the PDF nav-menu list helper.

``tenants.menus`` executes ``Tenant.objects.all()`` at module level (to
pre-populate ``simple_menu`` registries at startup).  Importing it at the
top of a test module would trigger that query during pytest collection,
before the test database is open, causing a RuntimeError.

For this reason ``distinct_requests`` is imported *inside* each test
function.  This is an intentional exception to the project's "no inner
imports" convention, documented here so future readers understand it is
not an oversight.
"""

import pytest
from django.utils.timezone import now


from pdf.models import Status
from pdf.models.request import PDFFile, ManualPDFTemplate  # noqa: F401 (used by fixtures)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _done_file(template, tenant, public=True):
    """Create a DONE PDFFile with a non-null .file path stub."""
    f = PDFFile.objects.create(
        template=template,
        tenant=tenant,
        filename=template.filename,
        status=Status.DONE,
        update_date=now(),
        scheduled_at=now(),
        public=public,
    )
    # Set a fake file path so file.file is truthy without touching disk.
    PDFFile.objects.filter(pk=f.pk).update(file="pdfs/fake/250101/test.pdf")
    f.refresh_from_db()
    return f


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_distinct_requests_empty_when_no_files(tenant, pdf_category):
    """Returns [] when no DONE PDFFiles exist."""
    from tenants.menus import distinct_requests  # see module docstring

    result = distinct_requests(tenant)
    assert result == []


@pytest.mark.parametrize(
    "template_fixture",
    [
        pytest.param("pdf_category", id="category"),
        pytest.param("manual_template", id="manual_template"),
    ],
)
def test_distinct_requests_shows_template_file(request, tenant, template_fixture):
    """Returns one MenuItem for a template (Category or ManualPDFTemplate) with a public DONE PDFFile."""
    from tenants.menus import distinct_requests  # see module docstring

    template = request.getfixturevalue(template_fixture)
    _done_file(template, tenant)
    result = distinct_requests(tenant)
    assert len(result) == 1


def test_distinct_requests_shows_orphan_public_done_file(tenant):
    """Orphaned (template=None) public DONE files appear in the menu."""
    from tenants.menus import distinct_requests  # see module docstring

    orphan = PDFFile.objects.create(
        template=None,
        tenant=tenant,
        filename="orphan",
        status=Status.DONE,
        update_date=now(),
        scheduled_at=now(),
        public=True,
    )
    PDFFile.objects.filter(pk=orphan.pk).update(file="pdfs/fake/250101/orphan.pdf")
    orphan.refresh_from_db()

    result = distinct_requests(tenant)
    assert len(result) == 1


def test_distinct_requests_hides_private_files(tenant, pdf_category):
    """Files with public=False are excluded from the menu."""
    from tenants.menus import distinct_requests  # see module docstring

    # Template-linked private file — must not appear.
    _done_file(pdf_category, tenant, public=False)
    assert distinct_requests(tenant) == []

    # Orphaned private file — also excluded.
    orphan = PDFFile.objects.create(
        template=None,
        tenant=tenant,
        filename="orphan",
        status=Status.DONE,
        update_date=now(),
        scheduled_at=now(),
        public=False,
    )
    PDFFile.objects.filter(pk=orphan.pk).update(file="pdfs/fake/250101/orphan.pdf")
    orphan.refresh_from_db()
    assert distinct_requests(tenant) == []


def test_distinct_requests_hides_non_done_files(tenant, pdf_category):
    """SCHEDULED, IN_PROGRESS, and FAILED files are not shown."""
    from tenants.menus import distinct_requests  # see module docstring

    for status in (Status.SCHEDULED, Status.IN_PROGRESS, Status.FAILED):
        PDFFile.objects.create(
            template=pdf_category,
            tenant=tenant,
            filename="test-cat",
            status=status,
            update_date=now(),
            scheduled_at=now(),
            public=True,
        )
    result = distinct_requests(tenant)
    assert result == []
