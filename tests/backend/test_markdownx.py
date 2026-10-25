"""Tests for the endpoints of the song editor."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

pytestmark = pytest.mark.django_db

UPLOAD_URL = reverse("markdownx_upload")
PREVIEW_URL = reverse("markdownx_markdownify")


def png():
    """A one pixel PNG."""
    buffer = io.BytesIO()
    Image.new("RGB", (1, 1)).save(buffer, "PNG")
    return SimpleUploadedFile("pixel.png", buffer.getvalue(), content_type="image/png")


@pytest.mark.parametrize("url", [UPLOAD_URL, PREVIEW_URL])
def test_anonymous_is_redirected_to_login(anon_client, url):
    """Visitors cannot use the editor endpoints."""
    response = anon_client.post(url, {"content": "{C}Hello", "image": png()})

    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


@pytest.mark.parametrize("url", [UPLOAD_URL, PREVIEW_URL])
def test_user_without_rights_is_forbidden(plain_client, url):
    """Logged in users who administer nothing cannot use the editor endpoints."""
    assert plain_client.post(url, {"content": "{C}Hello", "image": png()}).status_code == 403


def test_anonymous_upload_stores_nothing(anon_client, media_root):
    """A refused upload leaves the media directory empty."""
    anon_client.post(UPLOAD_URL, {"image": png()}, headers={"x-requested-with": "XMLHttpRequest"})

    assert not any(path.is_file() for path in media_root.rglob("*"))


def test_local_admin_can_upload(staff_client, media_root):
    """The song editor stores dropped images for tenant administrators."""
    response = staff_client.post(UPLOAD_URL, {"image": png()}, headers={"x-requested-with": "XMLHttpRequest"})

    assert response.status_code == 200
    assert "image_code" in response.json()
    assert any(path.is_file() for path in media_root.rglob("*"))


def test_local_admin_gets_the_preview(staff_client):
    """The preview renders the song markup."""
    response = staff_client.post(PREVIEW_URL, {"content": "{C}Hello"})

    assert response.status_code == 200
    assert b'class="chord"' in response.content
