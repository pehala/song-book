"""Tests for the PDF template filters."""

import pytest

from pdf.models.request import Status
from pdf.templatetags.types import get_status_color


@pytest.mark.parametrize(
    ("status", "color"),
    [
        pytest.param(Status.QUEUED, "yellow", id="queued"),
        pytest.param(Status.SCHEDULED, "yellow", id="scheduled"),
        pytest.param(Status.IN_PROGRESS, "blue", id="in progress"),
        pytest.param(Status.DONE, "green", id="done"),
        pytest.param(Status.FAILED, "red", id="failed"),
    ],
)
def test_every_status_has_a_color(status, color):
    """Each generation state is shown in its own colour"""
    assert get_status_color(str(status)) == color


def test_unknown_status_is_treated_as_a_failure():
    """Anything unexpected is flagged red"""
    assert get_status_color("??") == "red"
