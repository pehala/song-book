"""Tests for the Tenant models."""

import pytest
from django.core.exceptions import ValidationError

from tenants.models import Link, only_png

pytestmark = pytest.mark.django_db


class FakeUpload:
    """Stand in for an uploaded image field value."""

    def __init__(self, url, content_type=None):
        self.url = url
        self.file = type("File", (), {"content_type": content_type})()


def test_tenant_str_contains_name_and_id(tenant):
    """Tenants identify themselves by name and primary key."""
    assert str(tenant) == f"{tenant.name} ({tenant.id})"


def test_link_str_contains_display_name_and_url():
    """Links identify themselves by label and target."""
    link = Link(link="https://example.test", display_name="Example")

    assert str(link) == "Example (https://example.test)"


def test_only_png_accepts_png_uploads():
    """A freshly uploaded PNG passes validation."""
    only_png(FakeUpload(url="", content_type="image/png"))


def test_only_png_rejects_other_formats():
    """A freshly uploaded JPEG is refused."""
    with pytest.raises(ValidationError):
        only_png(FakeUpload(url="", content_type="image/jpeg"))


def test_only_png_skips_already_stored_files():
    """A file that is already stored is not re-validated."""
    only_png(FakeUpload(url="/media/uploads/logo.png"))
