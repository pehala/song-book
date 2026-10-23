"""Tests for the reusable view mixins."""

import pytest
from django.test import RequestFactory

from backend.mixins import RedirectToNextMixin


class Dummy(RedirectToNextMixin):
    """Minimal host class for the mixin under test"""

    success_url = "/fallback"

    def __init__(self, request):
        self.request = request


@pytest.mark.parametrize("method", ["get", "post"])
def test_next_parameter_wins(method):
    """A next parameter in either the query string or the body is honoured"""
    request = getattr(RequestFactory(), method)("/", {"next": "/target"})

    assert Dummy(request).get_success_url() == "/target"


def test_falls_back_to_success_url():
    """Without a next parameter the view's own success_url is used"""
    assert Dummy(RequestFactory().get("/")).get_success_url() == "/fallback"


def test_default_next_page_takes_precedence_over_success_url():
    """default_next_page overrides success_url when it is set"""
    view = Dummy(RequestFactory().get("/"))
    view.default_next_page = "/default"

    assert view.get_success_url() == "/default"
