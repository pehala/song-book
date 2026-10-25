"""Tests for the PDF template filters."""

import pytest

from pdf.models.request import Status
from pdf.templatetags.contents import last_word, without_last_word
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
    """Each generation state is shown in its own colour."""
    assert get_status_color(str(status)) == color


def test_unknown_status_is_treated_as_a_failure():
    """Anything unexpected is flagged red."""
    assert get_status_color("??") == "red"


@pytest.mark.parametrize(
    ("title", "head", "last"),
    [
        pytest.param("Hlupák Váhá", "Hlupák ", "Váhá", id="two words"),
        pytest.param("Jen se přiznej, že ti schází", "Jen se přiznej, že ti ", "schází", id="many words"),
        pytest.param("Amazonka", "", "Amazonka", id="one word"),
    ],
)
def test_title_is_split_before_its_last_word(title, head, last):
    """The last word, which the dots and the page number stay with, is separate from the rest of the title."""
    assert without_last_word(title) == head
    assert last_word(title) == last
    assert without_last_word(title) + last_word(title) == title
