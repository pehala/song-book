"""Constants and helpers the browser tests of the song editor share."""

import pytest

PHONE = {"width": 390, "height": 800}


DESKTOP = {"width": 1280, "height": 800}


DRAFT_STORED = "() => Object.keys(localStorage).some(key => key.startsWith('sb-draft:'))"


def lyrics(page):
    """Returns the locator of the textarea with the lyrics."""
    return page.locator("textarea.markdownx-editor")


def chip(page, name):
    """Returns the locator of the key of the chord bar that holds exactly this chord."""
    return page.locator("[data-chord]").get_by_text(name, exact=True)


def save_and_continue(page):
    """Presses the button that saves and stays, and waits for the page the server sends back."""
    page.set_viewport_size(DESKTOP)
    with page.expect_navigation():
        page.locator("button[name=continue]").click()


def wait_for_draft(page):
    """The draft is written a moment after the last change, and the page's policy forbids waiting with a string."""
    for _ in range(50):
        if page.evaluate(DRAFT_STORED):
            return
        page.wait_for_timeout(100)
    pytest.fail("no draft was stored")


def type_into_lyrics(page, text):
    """Replaces the lyrics with what a person typing `text` would leave."""
    box = lyrics(page)
    box.fill("")
    box.press_sequentially(text)


def drag(page, handle, dx):
    """Takes hold of the middle of a handle and moves it sideways by the given distance."""
    box = page.locator(handle).bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + dx / 2, y, steps=3)
    page.mouse.move(x + dx, y, steps=3)
    page.mouse.up()


def fold_arrow(page):
    """Returns the locator of the arrow on the details panel that folds it."""
    return page.locator("[data-fold-row] button")
