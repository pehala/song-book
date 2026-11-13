"""Tests for the app icons drawn from the songbook's logo and listed in the web app manifest."""

import io
import json
import math

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from PIL import Image, ImageChops

pytestmark = pytest.mark.django_db

MANIFEST_URL = reverse("frontend:manifest")


def test_manifest_lists_icons_drawn_from_the_logo(anon_client, logo):
    """The logo gives a plain and a maskable icon in both sizes browsers want."""
    icons = json.loads(anon_client.get(MANIFEST_URL).content)["icons"]

    assert [(icon["sizes"], icon["purpose"]) for icon in icons] == [
        ("192x192", "any"),
        ("192x192", "maskable"),
        ("512x512", "any"),
        ("512x512", "maskable"),
    ]
    assert icons[1]["src"].startswith(reverse("frontend:icon_maskable", kwargs={"size": 192}) + "?v=")


def test_icon_url_changes_with_the_logo(anon_client, logo):
    """A new logo is a new icon url, so the long-lived icon of the old one is never shown."""
    before = json.loads(anon_client.get(MANIFEST_URL).content)["icons"][0]["src"]
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "blue").save(buffer, "PNG")
    logo.icon.save("other.png", ContentFile(buffer.getvalue()))

    assert json.loads(anon_client.get(MANIFEST_URL).content)["icons"][0]["src"] != before


@pytest.mark.parametrize(
    "name,corner",
    [
        pytest.param("frontend:icon", (0, 0, 0, 0), id="plain"),
        pytest.param("frontend:icon_maskable", (249, 249, 249, 255), id="maskable"),
    ],
)
@pytest.mark.parametrize("size", [192, 512])
def test_icon_is_the_logo_on_a_square(anon_client, logo, name, corner, size):
    """The logo is fitted in a square of the size: on transparency, or on the app's background when maskable."""
    response = anon_client.get(reverse(name, kwargs={"size": size}))

    assert response["Content-Type"] == "image/png"
    assert "immutable" in response["Cache-Control"]
    with Image.open(io.BytesIO(response.content)) as icon:
        assert icon.size == (size, size)
        assert icon.getpixel((0, 0)) == corner
        assert icon.getpixel((size // 2, size // 2)) == (255, 0, 0, 255)


def test_maskable_icon_keeps_the_logo_inside_the_safe_zone(anon_client, logo):
    """A platform mask cuts a circle of 80% of the icon, so the logo stays well inside it."""
    response = anon_client.get(reverse("frontend:icon_maskable", kwargs={"size": 512}))

    with Image.open(io.BytesIO(response.content)) as icon:
        drawn = icon.convert("RGB")
        background = Image.new("RGB", icon.size, drawn.getpixel((0, 0)))
        left, top, right, bottom = ImageChops.difference(drawn, background).getbbox()
    # the corners of the logo's box lie inside the circle
    radius = 0.4 * 512
    assert all(math.dist((x, y), (256, 256)) <= radius for x in (left, right) for y in (top, bottom))
    assert right - left > 0.5 * 512


def test_icon_is_drawn_once(anon_client, logo, monkeypatch):
    """The icon is kept in the cache, so the logo is not resized on every request."""
    url = reverse("frontend:icon", kwargs={"size": 192})
    anon_client.get(url)
    monkeypatch.setattr("frontend.views.draw_icon", lambda *args: pytest.fail("drawn again"))

    assert anon_client.get(url).status_code == 200


@pytest.mark.parametrize(
    "source,size",
    [
        pytest.param("tenant", 192, id="no-logo"),
        pytest.param("logo", 64, id="unlisted-size"),
    ],
)
def test_icon_is_missing_without_a_logo_or_for_another_size(anon_client, request, source, size):
    """Only the sizes the manifest lists exist, and only for a tenant with a logo."""
    request.getfixturevalue(source)

    assert anon_client.get(reverse("frontend:icon", kwargs={"size": size})).status_code == 404


def test_icon_is_missing_for_a_logo_that_is_not_an_image(anon_client, tenant):
    """A stored logo Pillow cannot read gives no icon instead of a server error."""
    tenant.icon.save("logo.png", ContentFile(b"not a png"))

    assert anon_client.get(reverse("frontend:icon", kwargs={"size": 192})).status_code == 404


def test_manifest_survives_a_missing_logo_file(anon_client, tenant):
    """A logo that is no longer in the storage costs the icon, not the manifest."""
    tenant.icon = "uploads/gone.png"
    tenant.save()

    manifest = json.loads(anon_client.get(MANIFEST_URL).content)

    assert "icons" not in manifest
