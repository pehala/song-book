"""Browser tests of the splitter between the lyrics and the preview of the song editor."""

import pytest
from playwright.sync_api import expect

from tests.e2e.editor.helpers import DESKTOP, drag, lyrics


def test_wide_screen_can_drag_the_lyrics_wider_than_the_preview(editor):
    """A splitter between the text boxes gives one of them more of the width."""
    editor.set_viewport_size(DESKTOP)
    lyrics_before = lyrics(editor).bounding_box()["width"]
    preview_before = editor.locator("[data-panel=preview]").bounding_box()["width"]

    drag(editor, "[data-split]", dx=200)

    assert lyrics(editor).bounding_box()["width"] > lyrics_before + 150
    assert editor.locator("[data-panel=preview]").bounding_box()["width"] < preview_before - 150


def test_splitter_is_kept_and_limited(editor):
    """The share is remembered, and neither text box can be squeezed out."""
    editor.set_viewport_size(DESKTOP)
    drag(editor, "[data-split]", dx=-2000)
    least = lyrics(editor).bounding_box()["width"]

    editor.reload()

    assert lyrics(editor).bounding_box()["width"] == pytest.approx(least, abs=2)
    assert least > 150
    editor.locator("[data-split]").dblclick()
    assert lyrics(editor).bounding_box()["width"] > least + 150


def test_splitter_dragged_to_the_very_edge_keeps_the_lyrics_open(editor):
    """The left edge itself is a share of nothing, and still the lyrics keep their minimum."""
    editor.set_viewport_size(DESKTOP)
    edge = editor.locator(".sb-ed-work").bounding_box()["x"]
    handle = editor.locator("[data-split]").bounding_box()

    editor.mouse.move(handle["x"] + handle["width"] / 2, handle["y"] + handle["height"] / 2)
    editor.mouse.down()
    editor.mouse.move(edge + 100, handle["y"] + 10, steps=3)
    editor.mouse.move(edge, handle["y"] + 10)
    editor.mouse.up()

    assert lyrics(editor).bounding_box()["width"] > 150


def test_arrow_keys_move_the_splitter(editor):
    """The splitter is a focusable separator too."""
    editor.set_viewport_size(DESKTOP)
    before = lyrics(editor).bounding_box()["width"]
    editor.locator("[data-split]").focus()

    for _ in range(5):
        editor.keyboard.press("ArrowRight")

    assert lyrics(editor).bounding_box()["width"] > before + 40


def test_splitter_is_only_there_when_the_text_boxes_are_side_by_side(editor):
    """On a phone the lyrics and the preview are tabs, so there is nothing to split."""
    expect(editor.locator("[data-split]")).to_be_hidden()

    editor.set_viewport_size(DESKTOP)

    expect(editor.locator("[data-split]")).to_be_visible()
