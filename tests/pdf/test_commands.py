"""Tests for the generate_pdf management command."""

from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command

from pdf.models.request import PDFFile

pytestmark = pytest.mark.django_db


@pytest.fixture
def printed_category(make_category, tenant):
    return make_category(tenant, name="Printed", slug="printed", generate_pdf=True)


def test_every_printed_category_is_scheduled(printed_category, category, tenant):
    """Categories without PDF generation are left alone"""
    call_command("generate_pdf", tenant.id)

    assert PDFFile.objects.filter(template=printed_category).exists()
    assert not PDFFile.objects.filter(template=category).exists()


def test_a_single_tenant_can_be_selected(printed_category, make_category, other_tenant):
    """Passing tenant ids limits the command to those tenants"""
    foreign = make_category(other_tenant, name="Foreign", slug="foreign", generate_pdf=True)

    call_command("generate_pdf", printed_category.tenant_id)

    assert PDFFile.objects.filter(template=printed_category).exists()
    assert not PDFFile.objects.filter(template=foreign).exists()


def test_unknown_tenants_stop_the_command(printed_category):
    """A typo in the tenant ids schedules nothing at all"""
    call_command("generate_pdf", 999999)

    assert not PDFFile.objects.exists()


def test_media_directory_is_created(printed_category, tenant):
    """The output directory is prepared before scheduling"""
    call_command("generate_pdf", tenant.id)

    assert (Path(settings.MEDIA_ROOT) / settings.PDF_FILE_DIR).is_dir()


def test_running_without_tenants_covers_all_of_them(printed_category, make_category, other_tenant):
    """Without tenant ids every tenant is printed"""
    foreign = make_category(other_tenant, name="Foreign", slug="foreign", generate_pdf=True)

    call_command("generate_pdf")

    assert PDFFile.objects.filter(template=printed_category).exists()
    assert PDFFile.objects.filter(template=foreign).exists()
