"""Tests for the PDF storage helpers."""

import os

import pytest
from django.core.files.base import ContentFile
from django.utils.timezone import now

from pdf.models.request import PDFFile
from pdf.storage import DateOverwriteStorage

pytestmark = pytest.mark.django_db


@pytest.fixture
def stored_file(tenant):
    """A PDFFile with real bytes written to disk."""
    file = PDFFile.objects.create(tenant=tenant, filename="songbook", update_date=now())
    file.file.save("songbook.pdf", ContentFile(b"%PDF-"))
    return file


def test_existing_names_are_reused(tmp_path):
    """Saving over an existing name overwrites it instead of suffixing."""
    storage = DateOverwriteStorage(location=str(tmp_path))
    (tmp_path / "songbook.pdf").write_bytes(b"old")

    assert str(storage.get_available_name("songbook.pdf")) == "songbook.pdf"
    assert not (tmp_path / "songbook.pdf").exists()


def test_deleting_the_record_removes_the_file(stored_file):
    """The post_delete hook cleans the file off the disk."""
    path = stored_file.file.path

    stored_file.delete()

    assert not os.path.exists(path)


def test_deleting_a_record_without_a_file_is_harmless(tenant):
    """A record that never produced a file deletes cleanly."""
    file = PDFFile.objects.create(tenant=tenant, filename="songbook", update_date=now())

    file.delete()

    assert not PDFFile.objects.filter(pk=file.pk).exists()


def test_cleanup_ignores_records_whose_file_is_gone(tenant):
    """A record pointing at a file that is no longer there deletes cleanly."""
    file = PDFFile.objects.create(tenant=tenant, filename="songbook", update_date=now(), file="pdfs/missing.pdf")

    file.delete()

    assert not PDFFile.objects.filter(pk=file.pk).exists()


def test_cleanup_survives_a_failing_storage(stored_file, monkeypatch):
    """A storage that refuses to delete does not break the deletion."""

    def explode(*args, **kwargs):
        raise OSError("read only file system")

    monkeypatch.setattr(stored_file.file.storage, "delete", explode)

    stored_file.delete()

    assert not PDFFile.objects.filter(pk=stored_file.pk).exists()
