"""Browser tests of the details panel of the song editor and the arrow that folds it."""

import pytest
from django.urls import reverse
from playwright.sync_api import expect

from tests.e2e.editor.helpers import DESKTOP, PHONE, fold_arrow, lyrics


def test_arrow_is_only_for_wide_screens(editor):
    """On a phone the Details tab does that job."""
    expect(fold_arrow(editor)).to_be_hidden()

    editor.set_viewport_size(DESKTOP)

    expect(fold_arrow(editor)).to_be_visible()
    expect(fold_arrow(editor)).to_have_attribute("aria-expanded", "true")
    expect(editor.locator("[data-panel=details]").get_by_role("button")).to_have_count(1)


def test_arrow_is_on_the_details_not_in_the_bar(editor):
    """The control sits on the panel it folds."""
    editor.set_viewport_size(DESKTOP)

    arrow = fold_arrow(editor).bounding_box()
    panel = editor.locator("[data-panel=details]").bounding_box()

    assert panel["x"] <= arrow["x"] and arrow["x"] + arrow["width"] <= panel["x"] + panel["width"]
    assert panel["y"] <= arrow["y"] and arrow["y"] + arrow["height"] <= panel["y"] + panel["height"]
    expect(editor.locator(".sticky-top [aria-expanded]")).to_have_count(0)


def test_wide_screen_folds_the_details_into_a_rail_for_wider_text_boxes(editor):
    """Folding leaves a narrow rail with the arrow, and the text boxes take the rest of the room."""
    editor.set_viewport_size(DESKTOP)
    width = lyrics(editor).bounding_box()["width"]

    fold_arrow(editor).click()

    expect(editor.locator("input[name=name]")).to_be_hidden()
    expect(fold_arrow(editor)).to_have_attribute("aria-expanded", "false")
    expect(fold_arrow(editor)).to_have_attribute("title", "Show the details")
    rail = editor.locator("[data-panel=details]").bounding_box()
    assert rail["width"] < 80
    assert lyrics(editor).bounding_box()["width"] > width + 100

    fold_arrow(editor).click()

    expect(editor.locator("input[name=name]")).to_be_visible()
    assert lyrics(editor).bounding_box()["width"] == pytest.approx(width, abs=2)


def test_arrow_points_out_of_the_column_and_back_in(editor):
    """The arrow turns to show which way the details go."""
    editor.set_viewport_size(DESKTOP)
    turn = "button => getComputedStyle(button.querySelector('svg')).transform"

    open_turn = fold_arrow(editor).evaluate(turn)
    fold_arrow(editor).click()

    assert fold_arrow(editor).evaluate(turn) != open_turn


def test_folded_details_stay_folded_for_the_next_visit(editor):
    """The choice is remembered."""
    editor.set_viewport_size(DESKTOP)
    fold_arrow(editor).click()

    editor.reload()

    expect(editor.locator("input[name=name]")).to_be_hidden()
    expect(fold_arrow(editor)).to_have_attribute("title", "Show the details")


def test_phone_tab_shows_the_details_whatever_the_wide_screen_chose(editor):
    """The choice is for wide screens; the tabs of a phone are not affected by it."""
    editor.set_viewport_size(DESKTOP)
    fold_arrow(editor).click()
    editor.set_viewport_size(PHONE)

    editor.locator("#tab-details").click()

    expect(editor.locator("input[name=name]")).to_be_visible()


def test_details_unfold_for_a_field_the_browser_refuses(editor):
    """A required field that is folded away is shown again when the browser needs to point at it."""
    editor.set_viewport_size(DESKTOP)
    editor.locator("input[name=name]").fill("")
    fold_arrow(editor).click()
    expect(editor.locator("input[name=name]")).to_be_hidden()

    editor.locator("button[type=submit]:not([name=continue])").click()

    expect(editor.locator("input[name=name]")).to_be_visible()
    expect(fold_arrow(editor)).to_have_attribute("aria-expanded", "true")


def test_new_song_always_shows_its_details(page, library, superuser, sign_in):
    """Folding the details for good does not hide the fields a new song cannot do without."""
    sign_in(superuser)
    page.set_viewport_size(DESKTOP)
    page.goto(reverse("backend:add"))
    fold_arrow(page).click()
    expect(page.locator("input[name=name]")).to_be_hidden()

    page.goto(reverse("backend:add"))

    expect(page.locator("input[name=name]")).to_be_visible()
