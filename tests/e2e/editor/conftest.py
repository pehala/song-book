"""Fixtures of the browser tests of the song editor."""

import pytest
from django.urls import reverse
from playwright.sync_api import expect

from backend.models import Song
from tests.e2e.editor.helpers import PHONE


@pytest.fixture
def broken_scripts(page):
    """The errors the page's scripts throw, which a test can assert to be none."""
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    return errors


@pytest.fixture
def song(library):
    """The song the tests edit."""
    return Song.objects.get(name="Hrad")


@pytest.fixture
def editor(page, song, superuser, sign_in, broken_scripts):
    """Opens the editor of the song on a phone, once the server has rendered its preview."""
    sign_in(superuser)
    page.set_viewport_size(PHONE)
    page.goto(reverse("backend:edit", kwargs={"pk": song.pk}))
    expect(page.locator(".markdownx-preview ruby")).to_have_count(2)
    return page
