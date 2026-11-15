"""Browser tests of what the song editor types for the author: the chord bar, the braces and the line preview."""

import base64
import io
import re

import pytest
from PIL import Image
from playwright.sync_api import expect

from tests.e2e.editor.helpers import DESKTOP, PHONE, chip, coloured_text, lyrics, type_into_lyrics, wait_for_draft

COUNT_INPUTS = """() => {
    window.inputs = 0;
    document.querySelector("form[data-editor]").addEventListener("input", () => { window.inputs += 1; });
}"""

DROP_IMAGE = """png => {
    const bytes = Uint8Array.from(atob(png), character => character.charCodeAt(0));
    const files = new DataTransfer();
    files.items.add(new File([bytes], "picture.png", {type: "image/png"}));
    const drop = new DragEvent("drop", {dataTransfer: files, bubbles: true, cancelable: true});
    document.querySelector("textarea.markdownx-editor").dispatchEvent(drop);
}"""

# A little over the 500 ms markdownx waits after a change before it asks the server for the preview
MARKDOWNX_LATENCY = 700


def test_wide_screen_has_the_chord_bar_always(editor):
    """The chords can be clicked without the textarea having to be focused first."""
    editor.set_viewport_size(DESKTOP)

    expect(editor.locator(".sb-ed-keys")).to_be_visible()


def test_chord_bar_comes_with_the_keyboard(editor):
    """On a phone the bar is there while the lyrics are being typed, and not before."""
    expect(editor.locator(".sb-ed-keys")).to_be_hidden()

    lyrics(editor).click()

    expect(editor.locator(".sb-ed-keys")).to_be_visible()
    box = editor.locator(".sb-ed-keys").bounding_box()
    assert box["y"] + box["height"] <= PHONE["height"]


def test_chord_bar_offers_the_same_chords_in_the_same_order(editor):
    """The usual chords are always there, so a thumb finds them where it left them, whatever is typed."""
    lyrics(editor).click()
    chips = editor.locator("[data-chord]")

    expect(chips).to_have_text(["C", "D", "E", "F", "G", "Ami", "Emi"])
    type_into_lyrics(editor, "{Hmi}Nová {Dmi}slova {Hmi}")

    expect(chips).to_have_text(["C", "D", "E", "F", "G", "Ami", "Emi"])


def test_every_key_of_the_chord_bar_says_what_it_does_on_hover(editor):
    """The keys are small symbols, so each carries a text the pointer shows."""
    lyrics(editor).click()

    titles = editor.locator(".sb-ed-key").evaluate_all("keys => keys.map(key => key.title)")

    assert len(titles) == 11
    assert all(titles)
    assert titles[:4] == ["Undo", "Redo", "Insert an empty chord, to be typed between the braces", "Insert four spaces"]
    assert titles[4] == "Insert the chord C"


def test_chord_goes_in_front_of_the_selected_word(editor):
    """A chord is put at the start of the selection, the selected text stays, and the preview follows."""
    box = lyrics(editor)
    box.fill("{G}Na vrchu")
    box.click()
    box.evaluate("e => e.setSelectionRange(3, 5)")

    chip(editor, "D").click()

    expect(box).to_have_value("{G}{D}Na vrchu")
    expect(box).to_be_focused()
    expect(editor.locator(".markdownx-preview rt.chord")).to_have_text(["G", "D"], timeout=5000)


def test_empty_pair_of_braces_has_the_caret_inside(editor):
    """The chord key leaves the author inside the braces."""
    box = lyrics(editor)
    box.fill("")
    box.click()

    editor.locator(".sb-ed-key[data-insert='{}']").click()
    editor.keyboard.type("Ami")

    expect(box).to_have_value("{Ami}")


def test_undo_takes_back_an_inserted_chord(editor):
    """A chord put in by the bar is one step of the text's own history."""
    box = lyrics(editor)
    original = box.input_value()
    box.click()
    box.evaluate("e => e.setSelectionRange(0, 0)")

    chip(editor, "D").click()
    expect(box).to_have_value("{D}" + original)
    editor.locator(".sb-ed-key[data-command=undo]").click()

    expect(box).to_have_value(original)


def test_typing_an_opening_brace_closes_it(editor):
    """Typing a whole chord ends with exactly one closing brace, and the text after it is untouched."""
    type_into_lyrics(editor, "{Ami}word")

    expect(lyrics(editor)).to_have_value("{Ami}word")


def test_backspace_removes_an_empty_pair_of_braces(editor):
    """Changing one's mind about a chord does not leave a brace behind."""
    box = lyrics(editor)
    box.fill("")
    box.press_sequentially("{")
    expect(box).to_have_value("{}")

    box.press("Backspace")

    expect(box).to_have_value("")


def test_backspace_removes_an_empty_pair_when_the_browser_refuses_to_delete(editor):
    """Firefox refuses execCommand("delete") inside a beforeinput listener, and one Backspace must still do it."""
    editor.evaluate("document.execCommand = () => false")
    box = lyrics(editor)
    box.fill("")
    box.press_sequentially("{")
    expect(box).to_have_value("{}")

    box.press("Backspace")

    expect(box).to_have_value("")


def test_line_of_the_caret_is_previewed_above_the_keyboard(editor):
    """The preview is on another tab, so the line being typed is drawn next to the keys."""
    box = lyrics(editor)
    box.fill("{G}Na vrchu {D}stojí hrad")
    box.click()

    expect(editor.locator(".sb-ed-line ruby")).to_have_count(2, timeout=5000)


def test_line_preview_leaves_room_over_its_chords(editor):
    """The chords are drawn above the words, and the strip they sit in is not clipped against its top edge."""
    box = lyrics(editor)
    box.fill("{G}Na vrchu {D}stojí hrad")
    box.click()
    expect(editor.locator(".sb-ed-line rt.chord").first).to_be_visible(timeout=5000)

    gap = editor.evaluate(
        """() => {
            const strip = document.querySelector(".sb-ed-line").getBoundingClientRect();
            const chord = document.querySelector(".sb-ed-line rt.chord").getBoundingClientRect();
            return chord.top - strip.top;
        }"""
    )

    assert gap >= 8


def test_moving_the_caret_within_a_line_does_not_ask_the_server_again(editor):
    """The strip is drawn once for a line, not again at every step of the caret."""
    box = lyrics(editor)
    box.fill("Úvod\n{G}Na vrchu {D}stojí hrad")
    box.press("Control+End")
    expect(editor.locator(".sb-ed-line ruby")).to_have_count(2, timeout=5000)
    # The preview of the whole text is asked for at every key; only the strip asks for a single line
    lines = []
    editor.on("request", lambda request: lines.append(request) if "Úvod" not in (request.post_data or "") else None)

    for _ in range(3):
        box.press("ArrowLeft")
    editor.wait_for_timeout(800)

    assert [request.url for request in lines if "markdownify" in request.url] == []


@pytest.mark.parametrize(("typed", "changes"), [("abc", 3), ("{", 1)])
def test_a_typed_character_is_one_change(editor, typed, changes):
    """Typing is told once to everything that follows the text, not once by the browser and once more by the editor."""
    box = lyrics(editor)
    box.click()
    box.press("Control+End")
    editor.evaluate(COUNT_INPUTS)

    box.press_sequentially(typed)
    editor.wait_for_timeout(200)

    assert editor.evaluate("() => window.inputs") == changes


def test_an_image_dropped_into_the_lyrics_is_drawn_and_counted_as_a_change(editor, media_root):
    """The markup markdownx puts in for an uploaded image is coloured, counts as a change and goes in the draft."""
    editor.set_viewport_size(DESKTOP)
    picture = io.BytesIO()
    Image.new("RGB", (1, 1)).save(picture, "PNG")
    box = lyrics(editor)
    box.click()

    editor.evaluate(DROP_IMAGE, base64.b64encode(picture.getvalue()).decode())

    expect(box).to_have_value(re.compile(r"!\["))
    expect(editor.locator("[data-status]")).to_be_visible()
    assert coloured_text(editor) == box.input_value()
    wait_for_draft(editor)


@pytest.mark.parametrize("key", ["Tab", "Control+d"])
def test_what_markdownx_changes_by_a_key_is_drawn_and_counted_as_a_change(editor, key):
    """Indenting and duplicating a line show in the coloured text and mark the song as changed."""
    editor.set_viewport_size(DESKTOP)
    box = lyrics(editor)
    box.click()
    box.press("Control+Home")
    original = box.input_value()

    box.press(key)

    expect(box).not_to_have_value(original)
    expect(editor.locator("[data-status]")).to_be_visible()
    assert coloured_text(editor) == box.input_value()


def test_a_slow_preview_of_older_lyrics_does_not_replace_the_newer_one(editor):
    """The preview of the lyrics is the one of the last request, however the answers arrive.

    The one e2e test that touches the network: the real requests are held and let through in reverse order, because
    nothing else makes the server answer out of order. No response is faked.
    """
    held = []

    def hold(route):
        held.append(route)

    editor.route("**/markdownx/markdownify/", hold)
    box = lyrics(editor)

    box.fill("PRVNI")
    editor.wait_for_timeout(MARKDOWNX_LATENCY)
    box.fill("DRUHY")
    editor.wait_for_timeout(MARKDOWNX_LATENCY)
    for route in reversed(held):
        route.continue_()

    expect(editor.locator(".markdownx-preview")).to_have_text("DRUHY")
    editor.wait_for_timeout(MARKDOWNX_LATENCY)
    expect(editor.locator(".markdownx-preview")).to_have_text("DRUHY")
