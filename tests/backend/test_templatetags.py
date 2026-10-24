"""Tests for the backend template tags and filters."""

import pytest
from django.test import RequestFactory

from backend.templatetags.utils import datatables_language, prefix


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


@pytest.mark.parametrize(
    ("value", "argument", "expected"),
    [
        pytest.param("name", "Song: ", "Song: name", id="value gets the prefix"),
        pytest.param("", "Song: ", "", id="empty value is left alone"),
        pytest.param("0", "#", "#0", id="zero is still a value"),
    ],
)
def test_prefix(value, argument, expected):
    """The prefix filter only decorates non-empty values"""
    assert prefix(value, argument) == expected


def test_datatables_language_for_czech(request_with_language):
    """Czech pages load the translated datatables strings"""
    result = datatables_language(FakeContext(request_with_language("cs")))

    assert "datatables/cs.json" in result


def test_datatables_language_for_english(request_with_language):
    """Other languages use the datatables defaults"""
    assert datatables_language(FakeContext(request_with_language("en"))) == ""
