"""Tests for the backend template tags and filters."""

import pytest
from django.test import RequestFactory

from backend.templatetags.utils import datatables_language


class FakeContext(dict):
    """Template context stub exposing both item access and .request"""

    def __init__(self, request, **kwargs):
        super().__init__(**kwargs)
        self.request = request


@pytest.fixture
def request_with_language():
    def build(language):
        request = RequestFactory().get("/")
        request.LANGUAGE_CODE = language
        return request

    return build


def test_datatables_language_for_czech(request_with_language):
    """Czech pages load the translated datatables strings"""
    result = datatables_language(FakeContext(request_with_language("cs")))

    assert "datatables/cs.json" in result


def test_datatables_language_for_english(request_with_language):
    """Other languages use the datatables defaults"""
    assert datatables_language(FakeContext(request_with_language("en"))) == ""
