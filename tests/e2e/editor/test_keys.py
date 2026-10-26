"""Browser tests of what the song editor types for the author: the chord bar, the braces and the line preview."""

from playwright.sync_api import expect

from tests.e2e.editor.helpers import DESKTOP, PHONE, chip, lyrics, type_into_lyrics


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
