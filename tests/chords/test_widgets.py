"""Tests for the shared form widgets."""

import pytest
from django.http import QueryDict

from chords.widgets import AppendWidget, NoopWidget, PrependWidget


@pytest.mark.parametrize(
    ("widget_class", "expected_order"),
    [
        pytest.param(AppendWidget, ("input", "span"), id="addon after the input"),
        pytest.param(PrependWidget, ("span", "input"), id="addon before the input"),
    ],
)
def test_addon_widgets_wrap_the_input(widget_class, expected_order):
    """Both widgets render a bootstrap input group around the field"""
    rendered = widget_class(".pdf").render("filename", "songbook")

    assert "input-group" in rendered
    assert ".pdf" in rendered
    first, second = expected_order
    assert rendered.index(f"<{first}") < rendered.index(f"<{second}")


def test_noop_widget_renders_nothing():
    """The noop widget is invisible in the form"""
    assert NoopWidget().render("songs", [1, 2]) == ""


def test_noop_widget_is_hidden():
    """The noop widget does not take part in the visible layout"""
    assert NoopWidget().is_hidden is True


def test_noop_widget_reads_every_submitted_value():
    """Multi valued data is read with getlist"""
    data = QueryDict("songs=1&songs=2")

    assert NoopWidget().value_from_datadict(data, {}, "songs") == ["1", "2"]


def test_noop_widget_reads_plain_dicts():
    """Plain dictionaries without getlist still work"""
    assert NoopWidget().value_from_datadict({"songs": [1]}, {}, "songs") == [1]
