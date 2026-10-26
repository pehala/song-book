"""Browser tests of how the song editor lays itself out on a phone and on a wide screen."""

import pytest
from django.urls import reverse
from playwright.sync_api import expect

from tests.e2e.editor.helpers import DESKTOP, PHONE, fold_arrow, lyrics
from tests.e2e.test_layout import contrast

TOUCH_TARGETS = ".sb-ed button, .sb-ed a, .sb-ed summary, .sb-ed input:not([type=checkbox]), .sb-ed .form-check"
NEAR_TOP_IS_ON_TOP = """e => {
    const box = e.getBoundingClientRect();
    return e.contains(document.elementFromPoint(box.x + box.width / 2, box.y + 8));
}"""
CHORD_STYLE = "e => { const s = getComputedStyle(e); return [s.color, s.fontSize, s.fontWeight, s.lineHeight]; }"


def test_scripts_run_without_errors(editor, broken_scripts):
    """Loading the module and using the tabs throws nothing."""
    editor.locator("#tab-preview").click()

    assert broken_scripts == []


def test_preview_draws_chords_like_the_reader(page, editor):
    """The preview of the editor and the open song of the reader share their chord styles."""
    editor.locator("#tab-preview").click()
    in_editor = editor.locator(".markdownx-preview rt.chord").first.evaluate(CHORD_STYLE)

    page.goto("/categories/cs")
    page.locator("details.song summary", has_text="Hrad").click()
    in_reader = page.locator("details.song[open] rt.chord").first.evaluate(CHORD_STYLE)

    assert in_editor == in_reader


def test_phone_shows_one_section_at_a_time(editor):
    """The sections are tabs, and the lyrics are the one an existing song opens on."""
    expect(editor.locator("#tab-lyrics")).to_have_attribute("aria-selected", "true")
    expect(lyrics(editor)).to_be_visible()
    expect(editor.locator("input[name=name]")).to_be_hidden()
    expect(editor.locator(".markdownx-preview")).to_be_hidden()

    editor.locator("#tab-preview").click()
    expect(editor.locator(".markdownx-preview")).to_be_visible()
    expect(lyrics(editor)).to_be_hidden()

    editor.locator("#tab-details").click()
    expect(editor.locator("input[name=name]")).to_be_visible()
    expect(lyrics(editor)).to_be_hidden()


def test_tabs_follow_the_arrow_keys(editor):
    """A keyboard moves between the tabs the way a tab list is expected to."""
    editor.locator("#tab-lyrics").focus()

    editor.keyboard.press("ArrowRight")

    expect(editor.locator("#tab-preview")).to_have_attribute("aria-selected", "true")
    expect(editor.locator("#tab-preview")).to_be_focused()


def test_lyrics_fill_the_phone_screen(editor):
    """The editor is not pushed below the details, and the whole page fits the screen."""
    box = lyrics(editor).bounding_box()

    assert box["y"] < 250
    assert box["y"] + box["height"] <= PHONE["height"]
    assert editor.evaluate("document.documentElement.scrollHeight") <= PHONE["height"]


def test_wide_screen_shows_the_lyrics_beside_their_preview(editor):
    """From 1200px there are no tabs: the details, the lyrics and the preview are all there."""
    editor.set_viewport_size(DESKTOP)

    expect(editor.locator(".sb-ed-tabs")).to_be_hidden()
    expect(editor.locator("input[name=name]")).to_be_visible()
    lyrics_box = lyrics(editor).bounding_box()
    preview_box = editor.locator(".markdownx-preview").bounding_box()
    assert lyrics_box["x"] + lyrics_box["width"] <= preview_box["x"]


@pytest.mark.parametrize("menu", ["Options", "Account"])
def test_header_menus_open_over_the_sticky_bar(editor, menu):
    """A menu of the site header is not hidden behind the bar with the title and the save buttons."""
    editor.set_viewport_size(DESKTOP)

    editor.locator("summary", has_text=menu).click()

    panel = editor.locator("details[open] .sb-panel")
    expect(panel).to_be_visible()
    assert panel.evaluate(NEAR_TOP_IS_ON_TOP)


def test_new_song_opens_on_its_details(page, library, superuser, sign_in):
    """A song cannot be saved without a name and a category, so they are what a new song opens on."""
    sign_in(superuser)
    page.set_viewport_size(PHONE)

    page.goto(reverse("backend:add"))

    expect(page.locator("#tab-details")).to_have_attribute("aria-selected", "true")
    expect(page.locator("input[name=categories]").first).to_be_visible()


def test_missing_name_is_shown_where_it_is_wanted(editor):
    """A field the browser refuses to submit is on screen, though it sits on a tab nobody is looking at."""
    editor.locator("#tab-details").click()
    editor.locator("input[name=name]").fill("")
    editor.locator("#tab-lyrics").click()

    editor.locator("button[type=submit]:not([name=continue])").click()

    expect(editor.locator("#tab-details")).to_have_attribute("aria-selected", "true")
    expect(editor.locator("input[name=name]")).to_be_visible()


def test_phone_controls_are_big_enough_to_touch(editor):
    """Every button, field, tab and row of a checkbox list is at least 44px tall, and text is not smaller than 16px."""
    editor.locator("#tab-details").click()

    sizes = editor.evaluate(
        """(selector) => [...document.querySelectorAll(selector)]
            .filter(element => element.offsetParent !== null)
            .map(element => {
                const label = element.textContent.trim().slice(0, 20) || element.name;
                return [label, element.getBoundingClientRect().height];
            })""",
        TOUCH_TARGETS,
    )

    assert sizes
    assert [name for name, height in sizes if height < 43.5] == []
    editor.locator("#tab-lyrics").click()
    lyrics(editor).click()
    keys = editor.locator(".sb-ed-key").evaluate_all("keys => keys.map(key => key.getBoundingClientRect().height)")
    assert keys
    assert min(keys) >= 43.5
    assert editor.evaluate("parseFloat(getComputedStyle(document.querySelector('textarea')).fontSize)") >= 16


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_chord_colour_is_readable_in_both_themes(page, song, superuser, sign_in, theme):
    """The chords of the preview meet WCAG AA against the page, whichever theme it follows."""
    page.emulate_media(color_scheme=theme)
    sign_in(superuser)
    page.goto(reverse("backend:edit", kwargs={"pk": song.pk}))
    expect(page.locator(".markdownx-preview rt.chord").first).to_be_visible()

    chord = page.locator(".markdownx-preview rt.chord").first.evaluate("e => getComputedStyle(e).color")
    background = page.evaluate(
        """() => {
            const probe = document.createElement("div");
            probe.style.color = getComputedStyle(document.documentElement).getPropertyValue("--bg");
            document.body.append(probe);
            return getComputedStyle(probe).color;
        }"""
    )

    assert contrast(chord, background) >= 4.5


@pytest.mark.parametrize("size", [pytest.param(PHONE, id="phone"), pytest.param(DESKTOP, id="desktop")])
def test_all_the_metadata_is_shown_at_every_size(page, editor, size):
    """Every field of the song, the PDF options too, is never folded away, and the fields are big enough."""
    page.set_viewport_size(size)
    if size is PHONE:
        page.locator("#tab-details").click()

    for field in ("name", "author", "capo", "categories", "link", "archived", "pdf_columns", "pdf_keep_verses"):
        expect(page.locator(f"[name={field}]").first).to_be_visible()
    for field in ("name", "author", "capo"):
        assert page.locator(f"[name={field}]").first.bounding_box()["height"] >= 43.5


def test_pdf_indicator_is_in_the_bar_on_every_tab(editor):
    """The PDF warnings are in the bar with the buttons, so they are in view whichever section is open."""
    indicator = editor.locator(".sticky-top [data-pdf-pages]")

    for tab in ("details", "lyrics", "preview"):
        editor.locator(f"#tab-{tab}").click()
        expect(indicator).to_be_visible()
    expect(editor.locator("[data-panel] [data-pdf-pages]")).to_have_count(0)


def test_syntax_help_is_with_the_details_and_open_until_closed(editor):
    """The help on the markup is on the details."""
    editor.locator("#tab-details").click()
    help_box = editor.locator("#panel-details details")

    expect(help_box.get_by_text("Displays the chord above the word")).to_be_visible()
    expect(help_box.get_by_text("Adds N empty spaces")).to_be_visible()

    help_box.locator("summary").click()

    expect(help_box.get_by_text("Displays the chord above the word")).to_be_hidden()


def test_preview_follows_the_lyrics_as_they_are_scrolled_on_a_wide_screen(editor):
    """Beside the lyrics, the preview scrolls with them."""
    editor.set_viewport_size(DESKTOP)
    lyrics(editor).fill("\n\n".join(f"{{C}}Line {number}" for number in range(150)))
    expect(editor.locator(".markdownx-preview ruby")).to_have_count(150)

    lyrics(editor).evaluate("e => { e.scrollTop = e.scrollHeight; }")

    for _ in range(50):
        if editor.locator("[data-panel=preview]").evaluate("e => e.scrollTop") > 0:
            return
        editor.wait_for_timeout(100)
    pytest.fail("the preview did not follow the lyrics")


def test_long_details_scroll_in_their_column_on_a_wide_screen(editor):
    """The page keeps the height of the screen, so the text boxes stay in view while the details are scrolled."""
    editor.set_viewport_size({"width": 1280, "height": 600})

    page_height = editor.evaluate("document.documentElement.scrollHeight")
    column = editor.locator("#panel-details")
    assert page_height <= 600
    assert column.evaluate("e => e.scrollHeight > e.clientHeight")
    column.locator("[name=pdf_keep_verses]").scroll_into_view_if_needed()
    expect(column.locator("[name=pdf_keep_verses]")).to_be_in_viewport()


def test_wide_screen_puts_the_details_beside_the_text_boxes(editor):
    """From 1200px the details are a column, so the text boxes keep the whole height."""
    editor.set_viewport_size(DESKTOP)

    meta = editor.locator("[data-panel=details]").bounding_box()
    lyrics_box = lyrics(editor).bounding_box()
    assert meta["x"] + meta["width"] <= lyrics_box["x"]
    assert abs(meta["y"] - editor.locator(".sb-ed-work").bounding_box()["y"]) < 20
    assert lyrics_box["height"] > 450


@pytest.mark.parametrize("width", [pytest.param(1024, id="1024"), pytest.param(1199, id="1199")])
def test_below_1200_pixels_the_sections_are_still_tabs(editor, width):
    """There is one wide layout, so anything narrower than it gets the tabs of a phone."""
    editor.set_viewport_size({"width": width, "height": 800})

    expect(editor.locator(".sb-ed-tabs")).to_be_visible()
    expect(editor.locator("input[name=name]")).to_be_hidden()
    expect(editor.locator("[data-split]")).to_be_hidden()
    expect(fold_arrow(editor)).to_be_hidden()
