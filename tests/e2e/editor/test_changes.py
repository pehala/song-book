"""Browser tests of the unsaved changes of the song editor: their mark, the guard, the draft and saving."""

import re

import pytest
from django.urls import reverse
from playwright.sync_api import expect

from backend.models import Song
from tests.e2e.editor.helpers import (
    DESKTOP,
    DRAFT_STORED,
    PHONE,
    lyrics,
    save_and_continue,
    type_into_lyrics,
    wait_for_draft,
)

LEAVE_PREVENTED = """() => {
    const event = new Event("beforeunload", {cancelable: true});
    window.dispatchEvent(event);
    return event.defaultPrevented;
}"""


def test_unsaved_changes_are_marked(editor):
    """Nothing is marked until something changes, and then the bar says so."""
    expect(editor.locator("[data-status]")).to_be_hidden()

    lyrics(editor).press_sequentially("x")

    expect(editor.locator("[data-status]")).to_be_visible()


def test_leaving_with_unsaved_changes_is_questioned(editor):
    """The browser is asked to confirm before it throws a changed song away."""
    lyrics(editor).press_sequentially("x")

    assert editor.evaluate(LEAVE_PREVENTED) is True


def test_leaving_without_changes_is_not_questioned(editor):
    """Visiting the editor and going back asks nothing."""
    assert editor.evaluate(LEAVE_PREVENTED) is False


def test_leaving_after_a_change_that_was_undone_is_not_questioned(editor):
    """Typing something and taking it back again leaves nothing to lose."""
    box = lyrics(editor)
    original = box.input_value()
    box.press_sequentially("x")
    box.fill(original)

    assert editor.evaluate(LEAVE_PREVENTED) is False


def test_draft_is_offered_after_the_page_was_lost(editor):
    """A song typed into and then left comes back when the editor is opened again."""
    editor.on("dialog", lambda dialog: dialog.accept())
    lyrics(editor).press_sequentially("{Emi}")
    wait_for_draft(editor)

    editor.reload()
    expect(editor.locator("[data-draft]")).to_be_visible()
    expect(editor.locator("[data-draft-stale]")).to_be_hidden()
    editor.locator("[data-draft-restore]").click()

    expect(lyrics(editor)).to_have_value(re.compile(r"\{Emi\}"))
    expect(editor.locator("[data-draft]")).to_be_hidden()
    expect(editor.locator("[data-status]")).to_be_visible()


def test_draft_can_be_discarded(editor):
    """Discarding forgets it for good."""
    editor.on("dialog", lambda dialog: dialog.accept())
    lyrics(editor).press_sequentially("x")
    wait_for_draft(editor)
    editor.reload()

    editor.locator("[data-draft-discard]").click()
    editor.reload()

    expect(editor.locator("[data-draft]")).to_be_hidden()


def test_draft_says_when_the_song_changed_meanwhile(editor, song):
    """Restoring over somebody else's edit is not done unwarned."""
    editor.on("dialog", lambda dialog: dialog.accept())
    lyrics(editor).press_sequentially("x")
    wait_for_draft(editor)
    editor.wait_for_load_state("networkidle")
    Song.objects.filter(pk=song.pk).update(author="Someone else")

    editor.reload()

    expect(editor.locator("[data-draft-stale]")).to_be_visible()


def test_saving_forgets_the_draft(editor, song):
    """A saved song leaves no draft behind to be offered later."""
    lyrics(editor).press_sequentially("{Emi}")
    wait_for_draft(editor)

    save_and_continue(editor)

    assert editor.evaluate(DRAFT_STORED) is False
    expect(editor.locator("[data-draft]")).to_be_hidden()


def test_a_failed_save_keeps_the_draft(editor, song):
    """The connection dies as the form is sent: the page is lost, the edits are not."""
    type_into_lyrics(editor, "{Emi}Bez spojení")
    editor.context.set_offline(True)

    editor.locator("button[type=submit]:not([name=continue])").click()
    editor.wait_for_url("chrome-error://chromewebdata/")
    editor.context.set_offline(False)
    editor.goto(reverse("backend:edit", kwargs={"pk": song.pk}))

    expect(editor.locator("[data-draft]")).to_be_visible()
    editor.locator("[data-draft-restore]").click()
    expect(lyrics(editor)).to_have_value("{Emi}Bez spojení")


def test_a_saved_new_song_leaves_no_draft_for_the_next_one(page, library, superuser, sign_in):
    """Saving goes on to the reader, and the editor that is opened next starts without an offer of the last song."""
    sign_in(superuser)
    page.set_viewport_size(PHONE)
    page.goto(reverse("backend:add"))
    page.locator("input[name=name]").fill("Nová")
    page.locator("input[name=capo]").fill("0")
    page.locator("input[name=categories]").first.check()
    page.locator("#tab-lyrics").click()
    lyrics(page).fill("{C}Text")
    wait_for_draft(page)

    page.locator("button[type=submit]:not([name=continue])").click()
    page.wait_for_url(lambda url: "/add" not in url)
    page.goto(reverse("backend:add"))

    expect(page.locator("[data-draft]")).to_be_hidden()
    assert page.evaluate(DRAFT_STORED) is False


def test_save_and_continue_stays_in_the_editor(editor, song):
    """The song is stored and the author is still in front of it."""
    type_into_lyrics(editor, "{Emi}Nový text")

    save_and_continue(editor)

    song.refresh_from_db()
    assert song.text == "{Emi}Nový text"
    expect(lyrics(editor)).to_have_value("{Emi}Nový text")


def test_dismissing_the_message_after_saving_does_not_scroll_the_page(editor, song):
    """The form moves up when the success message goes, and it is made as tall again as the room it has."""
    save_and_continue(editor)
    height = editor.evaluate("document.documentElement.scrollHeight")
    assert height <= DESKTOP["height"]

    editor.locator(".alert-success .btn-close").click()

    expect(editor.locator(".alert-success")).to_have_count(0)
    editor.wait_for_function(f"document.documentElement.scrollHeight <= {DESKTOP['height']}")
    assert editor.evaluate("document.documentElement.scrollHeight") <= DESKTOP["height"]
    box = lyrics(editor).bounding_box()
    assert box["y"] + box["height"] == pytest.approx(DESKTOP["height"], abs=40)


def test_ctrl_s_saves_and_continues(editor, song):
    """The shortcut of every editor saves without leaving the page."""
    type_into_lyrics(editor, "{Emi}Z klávesnice")

    with editor.expect_navigation():
        editor.keyboard.press("Control+s")

    song.refresh_from_db()
    assert song.text == "{Emi}Z klávesnice"


def test_save_goes_back_to_the_reader(editor, song):
    """The primary button saves and leaves the editor."""
    editor.locator("button[type=submit]:not([name=continue])").click()

    editor.wait_for_url(lambda url: "/edit/" not in url)
    editor.wait_for_load_state("networkidle")
