"""Browser tests of the reader's layout rules: touch targets, form fonts, contrast and reduced motion."""

import itertools

import pytest
from playwright.sync_api import expect

PHONE = {"width": 375, "height": 740}

CONTROLS = "button, a, summary, select, input:not([type=checkbox])"
SIZES = """(selector) => [...document.querySelectorAll(selector)]
    .filter(element => element.offsetParent !== null)
    .map(element => {
        const rect = element.getBoundingClientRect();
        const label = element.textContent || element.getAttribute("aria-label") || element.id || "";
        const name = `${element.tagName.toLowerCase()} ${label.trim().slice(0, 20)}`;
        const fontSize = parseFloat(getComputedStyle(element).fontSize);
        return [name, Math.round(rect.width), Math.round(rect.height), fontSize];
    })"""


def luminance(color):
    channels = [
        int(value) / 255 for value in color.removeprefix("rgb(").removeprefix("rgba(").removesuffix(")").split(",")[:3]
    ]
    linear = [value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground, background):
    lighter, darker = sorted([luminance(foreground), luminance(background)], reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def colors(page, selector):
    return page.evaluate(
        """(selector) => {
            const element = document.querySelector(selector);
            const transparent = "rgba(0, 0, 0, 0)";
            let background = element;
            while (background && getComputedStyle(background).backgroundColor === transparent) {
                background = background.parentElement;
            }
            return [getComputedStyle(element).color, getComputedStyle(background).backgroundColor];
        }""",
        selector,
    )


def open_everything(page):
    page.locator(".sb-burger").click()
    for dropdown in page.locator("details.sb-dd").all():
        dropdown.locator("summary").click()
    page.locator("details.song summary").first.click()


@pytest.fixture
def phone(page, library):
    page.set_viewport_size(PHONE)
    page.goto("/categories/cs")
    expect(page.locator("details.song").first).to_be_visible()
    return page


def test_controls_are_at_least_44px_on_a_phone(phone):
    """Header, menus, options and the song's tools are big enough for a thumb"""
    open_everything(phone)

    too_small = [item[:3] for item in phone.evaluate(SIZES, CONTROLS) if item[1] < 44 or item[2] < 44]

    assert too_small == []


def test_form_fields_use_at_least_16px_text(phone):
    """Smaller text makes iOS zoom the page when a field gets focus"""
    open_everything(phone)

    fields = phone.evaluate(SIZES, "select, input:not([type=checkbox])")

    assert [item[0] for item in fields if item[3] < 16] == []


def test_phone_layout_does_not_scroll_sideways(phone):
    """Everything fits the width of the screen"""
    open_everything(phone)

    assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_desktop_menu_is_a_row_without_hamburger(page, library):
    """Wide screens get the menu in the bar, the phone layout is the base"""
    page.set_viewport_size({"width": 1200, "height": 700})
    page.goto("/categories/cs")

    expect(page.locator(".sb-burger")).to_be_hidden()
    expect(page.locator("summary", has_text="Categories")).to_be_visible()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_text_has_enough_contrast(page, library, theme):
    """Menu entries, muted text and primary buttons meet WCAG AA (4.5:1) in both themes"""
    page.add_init_script(f"localStorage.setItem('theme', '{theme}')")
    page.goto("/categories/cs")
    page.locator("details.song summary").first.click()
    expect(page.locator(".song-text")).to_be_visible()

    for selector in ("header .sb-dd > summary", "header .sb-brand", ".song small", ".sb-btn.sb-primary", ".song h2"):
        foreground, background = colors(page, selector)
        assert contrast(foreground, background) >= 4.5, (theme, selector, foreground, background)


def test_reduced_motion_stops_the_animations(page, library):
    """Songs open and the chevron turns without transition for readers who ask for less motion"""
    page.emulate_media(reduced_motion="reduce")
    page.goto("/categories/cs")
    expect(page.locator("details.song").first).to_be_visible()

    durations = page.evaluate(
        """() => {
            const song = document.querySelector("details.song");
            const chevron = song.firstElementChild;
            return [
                getComputedStyle(song, "::details-content").transitionDuration,
                getComputedStyle(chevron, "::after").transitionDuration,
            ];
        }"""
    )

    assert set(durations) <= {"0s", ""}


def test_drawing_the_list_does_not_shift_the_page(page, library):
    """The list takes the place of the loader without moving what is around it"""
    page.add_init_script(
        """window.shifts = [];
        new PerformanceObserver(list => window.shifts.push(...list.getEntries().map(entry => entry.value)))
            .observe({type: "layout-shift", buffered: true});"""
    )
    page.goto("/categories/cs")
    expect(page.locator("details.song").first).to_be_visible()

    assert page.evaluate("window.shifts") == []


def test_lines_with_and_without_chords_are_spaced_alike(page, library, make_song):
    """A chord over a line does not push it away from its neighbours"""
    make_song(
        library.category_set.get(slug="cs"), name="Rhythm", text="{C}First line\nSecond line\n{G}Third line\nFourth"
    )
    page.goto("/categories/cs")
    page.locator("details.song", has_text="Rhythm").locator("summary").click()

    bottoms = page.evaluate(
        """() => {
            const text = [...document.querySelectorAll(".song-text")].at(-1);
            const walker = document.createTreeWalker(text, NodeFilter.SHOW_TEXT);
            const bottoms = [];
            for (let node = walker.nextNode(); node; node = walker.nextNode()) {
                if (!node.parentElement.closest("rt") && node.textContent.trim()) {
                    const range = document.createRange();
                    range.selectNodeContents(node);
                    bottoms.push(Math.round(range.getBoundingClientRect().bottom));
                }
            }
            return [...new Set(bottoms)];
        }"""
    )
    gaps = {after - before for before, after in itertools.pairwise(bottoms)}

    assert len(bottoms) == 4
    assert max(gaps) - min(gaps) <= 1, bottoms
