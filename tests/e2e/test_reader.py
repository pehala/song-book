"""Browser tests of the reader: routing, search, song view, options and the service worker."""

import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from django.contrib.staticfiles import finders
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

from frontend.views import ASSETS


def songs(page):
    """Returns the locator of the songs shown."""
    return page.locator("details.song")


def titles(page):
    """Returns the locator of the titles of the songs shown."""
    return page.locator("details.song h2")


def numbers(page):
    """Returns the locator of the numbers of the songs shown."""
    return page.locator("details.song .num")


def open_menu(page, name):
    """Opens the header menu with the given name."""
    page.locator("summary", has_text=name).click()


def go_to_category(page, name):
    """Opens the categories menu and follows the link to the category."""
    open_menu(page, "Categories")
    page.get_by_role("link", name=name).click()


def test_all_songs_is_the_first_entry_of_the_categories_menu(page, library):
    """All songs leads the categories in the menu."""
    page.goto("/categories/cs")
    open_menu(page, "Categories")

    entries = page.locator("details.sb-dd", has=page.locator("summary", has_text="Categories")).locator("a")
    expect(entries.first).to_have_text("All songs")


def test_landing_page_is_drawn_from_the_shell(page, library):
    """/ shows the tenant's landing page without a redirect from the server."""
    page.goto("/")

    expect(page).to_have_url(page.url.split("/", 3)[0] + "//" + urlsplit(page.url).netloc + "/categories/cs")
    expect(songs(page)).to_have_count(3)
    expect(page.locator("header .sb-brand")).to_have_text(library.display_name)
    expect(page).to_have_title(f"Česky | {library.display_name}")


def test_songs_are_numbered_and_archived_ones_hidden(page, library):
    """Anonymous visitors see the public songs of the category, numbered from 1."""
    page.goto("/categories/cs")

    expect(numbers(page)).to_have_text(["1.", "2.", "3."])
    expect(titles(page)).to_have_text(["Jožin z bažin", "Hrad", "Both Songs"])


def test_shell_placeholder_is_gone_once_the_reader_is_drawn(page, library):
    """The progress bar of the shell must not linger below the song list."""
    page.goto("/all")

    expect(songs(page)).to_have_count(4)
    expect(page.locator(".progress")).to_have_count(0)


def test_progress_bar_shows_while_the_first_list_downloads(page, library):
    """With nothing stored the reader shows a progress bar until the songs arrive."""
    held = []

    def hold(route):
        held.append(route)

    page.route("**/api/songs", hold)
    page.goto("/all")

    expect(page.locator("[role=progressbar].centered")).to_be_visible()
    expect(page.locator(".progress-caption")).to_contain_text("Loading songs")
    held[0].continue_()

    expect(songs(page)).to_have_count(4)
    expect(page.locator("[role=progressbar]")).to_have_count(0)


def test_download_progress_follows_the_announced_size(page, library):
    """The bytes read are reported against the size the server announces, and the list is stored whole."""
    page.goto("/all")
    expect(songs(page)).to_have_count(4)

    report = page.evaluate(
        """async () => {
            const {loadSongs} = await import("/static/app/store.js");
            const bytes = new TextEncoder().encode(JSON.stringify([{id: 1, number: 1}]));
            window.fetch = async () => new Response(
                new ReadableStream({
                    start(controller) {
                        controller.enqueue(bytes.slice(0, 5));
                        controller.enqueue(bytes.slice(5));
                        controller.close();
                    },
                }),
                {headers: {"X-Songs-Size": String(bytes.length), "ETag": '"e"'}},
            );
            const steps = [];
            let songs = null;
            await loadSongs("/api/songs-fake", list => (songs = list), step => steps.push(step));
            const stored = await (await caches.open("songs")).match("/api/songs-fake");
            return {steps, songs, size: bytes.length, etag: stored.headers.get("ETag")};
        }"""
    )

    assert report["steps"] == [
        {"loaded": 5, "total": report["size"]},
        {"loaded": report["size"], "total": report["size"]},
    ]
    assert report["songs"] == [{"id": 1, "number": 1}]
    assert report["etag"] == '"e"'


def test_progress_says_when_the_whole_list_is_fetched_again(page, library):
    """A delta that does not fit the stored list makes the reader fetch everything, which the progress reports."""
    page.goto("/all")
    expect(songs(page)).to_have_count(4)

    steps = page.evaluate(
        """async () => {
            const {loadSongs} = await import("/static/app/store.js");
            const headers = {"ETag": '"old"', "Date": new Date().toUTCString()};
            const cache = await caches.open("songs");
            await cache.put("/api/songs-fake", new Response('[{"id": 1, "number": 1}]', {headers}));
            const delta = {etag: '"new"', now: 0, ids: [1, 2], changed: []};
            const whole = [{id: 1, number: 1}, {id: 2, number: 2}];
            let calls = 0;
            window.fetch = async () => new Response(JSON.stringify(calls++ ? whole : delta));
            const steps = [];
            await loadSongs("/api/songs-fake", () => {}, step => steps.push(step));
            return steps;
        }"""
    )

    retried = [step for step in steps if step.get("retry")]
    assert retried[0] == {"loaded": 0, "total": 0, "retry": True}
    assert steps[-1].get("retry")
    assert not steps[0].get("retry")


def test_remaining_time_follows_the_recent_speed(page, library):
    """The estimate waits for a known speed and a total, and is left out for a stalled or nearly done download."""
    page.goto("/all")
    expect(songs(page)).to_have_count(4)

    estimates = page.evaluate(
        """async () => {
            const {remainingSeconds} = await import("/static/app/store.js");
            const at = (time, loaded) => ({time, loaded});
            return [
                remainingSeconds([at(0, 0), at(2000, 200)], 1000),
                remainingSeconds([at(0, 0), at(500, 100)], 1000),
                remainingSeconds([at(0, 100), at(2000, 100)], 1000),
                remainingSeconds([at(0, 0), at(2000, 990)], 1000),
                remainingSeconds([at(0, 0), at(2000, 200)], 0),
            ];
        }"""
    )

    assert estimates == [8, None, None, None, None]


def page_errors(page):
    """The uncaught errors the page raises."""
    errors = []

    def collect(error):
        errors.append(error)

    page.on("pageerror", collect)
    return errors


def throttle(page, bytes_per_second):
    """Makes the page's downloads arrive in chunks over several seconds."""
    session = page.context.new_cdp_session(page)
    session.send(
        "Network.emulateNetworkConditions",
        {"offline": False, "latency": 0, "downloadThroughput": bytes_per_second, "uploadThroughput": -1},
    )


def test_first_download_estimates_the_time_left(page, library, make_song):
    """Over a slow connection the caption of the bar tells how long the songs still take."""
    make_song(*library.category_set.all(), name="Long", text="{C}la " * 4000)
    errors = page_errors(page)
    throttle(page, 40_000)
    page.goto("/all")

    expect(page.locator(".progress-caption")).to_contain_text("left", timeout=15_000)
    expect(songs(page)).to_have_count(5, timeout=30_000)
    assert not errors


def test_options_reload_downloads_the_whole_list_again(page, library, requests_made):
    """The reload button fetches the full list rather than a delta and says so."""
    page.goto("/all")
    expect(songs(page)).to_have_count(4)
    requests_made.clear()

    open_menu(page, "Options")
    page.get_by_role("button", name="Reload songs").click()

    expect(page.get_by_text("The songs were reloaded")).to_be_visible()
    fetched = [url for method, url in requests_made if "/api/songs" in url]
    assert fetched
    assert not any("since" in url for url in fetched)
    expect(songs(page)).to_have_count(4)


def test_reload_over_a_slow_connection_draws_the_line_without_errors(page, library, make_song):
    """The line along the top follows a manual reload that arrives in chunks."""
    make_song(*library.category_set.all(), name="Long", text="{C}la " * 4000)
    errors = page_errors(page)
    page.goto("/all")
    expect(songs(page)).to_have_count(5)
    throttle(page, 40_000)

    open_menu(page, "Options")
    page.get_by_role("button", name="Reload songs").click()

    expect(page.locator("[role=progressbar]:not(.centered)")).to_be_visible(timeout=10_000)
    expect(page.get_by_text("The songs were reloaded")).to_be_visible(timeout=30_000)
    assert not errors


def test_switching_category_asks_the_server_for_nothing(page, library, requests_made):
    """The songs are held already, so changing category is a pushState and a filter."""
    page.goto("/categories/cs")
    expect(songs(page)).to_have_count(3)
    seen = len(requests_made)

    go_to_category(page, "English")

    expect(page).to_have_url(f"{urlsplit(page.url).scheme}://{urlsplit(page.url).netloc}/categories/en")
    expect(titles(page)).to_have_text(["Both Songs", "Amazing Grace"])
    assert [url for _, url in requests_made[seen:] if "/api/songs" in url or url.endswith("/categories/en")] == []


def test_back_button_returns_to_the_previous_category(page, library):
    """Client-side routes live in the history."""
    page.goto("/categories/cs")
    go_to_category(page, "English")
    expect(songs(page)).to_have_count(2)

    page.go_back()

    expect(songs(page)).to_have_count(3)


def test_unknown_category_says_so(page, library):
    """A slug nobody owns is explained, not left blank."""
    page.goto("/categories/nope")

    expect(page.get_by_text("This category does not exist.")).to_be_visible()


def test_everything_comes_from_one_origin(page, library, requests_made):
    """No CDN: the reader works on a connection that can reach nothing else."""
    page.goto("/categories/cs")
    expect(songs(page)).to_have_count(3)

    origins = {urlsplit(url).netloc for _, url in requests_made}

    assert origins == {urlsplit(page.url).netloc}


SEARCHES = {
    "/categories/cs": [
        ("JOZIN", ["Jožin z bažin"]),  # case and diacritics are ignored
        ("stojí hrad", ["Hrad"]),  # the lyrics are searched
        ("emi", ["Jožin z bažin"]),  # chords are part of the text
        ("mládek", ["Jožin z bažin"]),  # so is the author
        ("jedu;lesem", ["Jožin z bažin"]),  # `a;b` means both a and b
        ("jedu;hrad", []),
    ],
    "/categories/en": [("2", ["Amazing Grace"])],  # the numbers shown follow the route
}


@pytest.mark.parametrize("path", SEARCHES)
def test_search(page, library, path):
    """Searching ignores case and diacritics and looks into the text, the author and the number of the list."""
    page.goto(path)
    search = page.get_by_label("Search")

    for query, found in SEARCHES[path]:
        search.fill(query)
        expect(titles(page)).to_have_text(found)
        if not found:
            expect(page.get_by_text("No songs found")).to_be_visible()


def test_opening_a_song_shows_its_text(page, library):
    """The body is drawn when the song is opened."""
    page.goto("/categories/cs")

    songs(page).nth(1).locator("summary").click()

    expect(songs(page).nth(1).locator(".song-text")).to_contain_text("vrchu stojí")


def test_open_song_keeps_its_title_in_view(page, library, make_song):
    """The title of a long song stays under the search bar while its text scrolls past."""
    make_song(library.category_set.get(slug="cs"), name="Long", text="\n\n".join(f"{{C}}Verse {n}" for n in range(60)))
    page.emulate_media(reduced_motion="reduce")
    page.goto("/categories/cs")
    long = page.locator("details.song", has_text="Long")
    long.locator("summary").click()
    expect(long.locator(".song-text p")).to_have_count(60)

    page.evaluate("scrollTo(0, 1500)")

    search = page.locator(".search").bounding_box()
    expect(long.locator("summary")).to_be_in_viewport()
    assert long.locator("summary").bounding_box()["y"] == search["y"] + search["height"]


def open_long_song(page, library, make_song, verse="{C}Verse"):
    """Adds a song long enough to scroll, with reduced motion, and opens it."""
    make_song(
        library.category_set.get(slug="cs"),
        name="Long",
        author="Someone",
        text="\n\n".join(f"{verse} {n}" for n in range(60)),
    )
    page.emulate_media(reduced_motion="reduce")
    page.goto("/categories/cs")
    long = page.locator("details.song", has_text="Long")
    long.locator("summary").click()
    expect(long.locator(".song-text p")).to_have_count(60)
    page.wait_for_function("document.getAnimations({subtree: true}).length === 0")
    return long


def press_scroll_down(page):
    """Presses Scroll down until it goes away at the end of the song; returns the scroll positions before each press."""
    button = page.get_by_role("button", name="Scroll down")
    positions = []
    while button.count() and len(positions) < 30:
        positions.append(page.evaluate("scrollY"))
        try:
            button.click(timeout=1000)
        except PlaywrightTimeoutError:
            break
    return positions


def test_scroll_down_keeps_what_is_read_in_view(page, library, make_song):
    """A press moves a verse start up under the title by at most 80% of the screen, so what is read stays in view."""
    long = open_long_song(page, library, make_song)
    verses = long.locator(".song-text p")
    last_read = verses.evaluate_all(
        "verses => verses.findLastIndex(verse => verse.getBoundingClientRect().bottom <= innerHeight)"
    )
    before = page.evaluate("scrollY")

    page.get_by_role("button", name="Scroll down").click()

    title = long.locator("summary").bounding_box()
    below_title = title["y"] + title["height"]
    tops = verses.evaluate_all("verses => verses.map(verse => verse.getBoundingClientRect().top)")
    assert any(abs(top - (below_title + 8)) <= 1 for top in tops)
    assert page.evaluate("scrollY") - before <= 0.8 * (page.viewport_size["height"] - below_title)
    assert verses.nth(last_read).bounding_box()["y"] > below_title


def test_scroll_down_moves_on_when_a_verse_is_taller_than_the_screen(page, library, make_song):
    """With no verse start to align to, the button still scrolls most of a screen."""
    page.set_viewport_size({"width": 667, "height": 300})
    open_long_song(page, library, make_song, verse="word " * 300)
    before = page.evaluate("scrollY")

    page.get_by_role("button", name="Scroll down").click()

    assert page.evaluate("scrollY") > before


def test_scroll_down_never_goes_up_in_columns(page, library, make_song):
    """With several columns each press moves forward, whichever column the verses at the edge are in."""
    page.add_init_script("localStorage.setItem('columns', '2')")
    page.set_viewport_size({"width": 1280, "height": 800})
    open_long_song(page, library, make_song)

    positions = press_scroll_down(page)

    assert len(positions) > 2
    assert positions == sorted(set(positions))


def test_scroll_down_is_offered_only_while_the_song_continues(page, library, make_song):
    """A song that fits the screen has no button, a long one has it until its end is in view."""
    page.emulate_media(reduced_motion="reduce")
    page.goto("/categories/cs")
    songs(page).nth(1).locator("summary").click()
    expect(page.locator(".song-text p")).to_have_count(1)
    expect(page.get_by_role("button", name="Scroll down")).to_have_count(0)

    open_long_song(page, library, make_song)
    button = page.get_by_role("button", name="Scroll down")
    expect(button).to_be_visible()
    page.evaluate("scrollTo(0, document.documentElement.scrollHeight)")
    expect(button).to_have_count(0)
    page.evaluate("scrollTo(0, 0)")
    expect(button).to_be_visible()


def test_scroll_down_stops_at_the_end_of_the_song(page, library, make_song):
    """The last press leaves the end of the song at the bottom edge, with the next songs still below the screen."""
    long = open_long_song(page, library, make_song)

    press_scroll_down(page)

    expect(page.get_by_role("button", name="Scroll down")).to_have_count(0)
    last = long.locator(".song-text p").last.bounding_box()
    assert 0 <= page.viewport_size["height"] - (last["y"] + last["height"]) <= 9


def test_one_song_is_open_at_a_time(page, library):
    """Opening a song closes the previous one."""
    page.goto("/categories/cs")

    songs(page).nth(0).locator("summary").click()
    songs(page).nth(1).locator("summary").click()

    expect(page.locator("details.song[open]")).to_have_count(1)
    expect(songs(page).nth(1)).to_have_attribute("open", "")


def test_random_song_button_opens_a_song_of_the_list(page, library):
    """The button opens one song of the category, and another one each time."""
    page.goto("/categories/cs")

    page.get_by_role("button", name="Random song").click()

    expect(page.locator("details.song[open]")).to_have_count(1)
    first = page.locator("details.song[open] h2").inner_text()
    page.get_by_role("button", name="Random song").click()
    expect(page.locator("details.song[open]")).to_have_count(1)
    expect(page.locator("details.song[open] h2")).not_to_have_text(first)


def test_random_song_button_follows_the_search(page, library):
    """Only the songs left by the search are drawn from, and the button is off when none is."""
    page.goto("/categories/cs")
    page.get_by_label("Search").fill("hrad")

    page.get_by_role("button", name="Random song").click()

    expect(page.locator("details.song[open] h2")).to_have_text("Hrad")
    page.get_by_label("Search").fill("zzzz")
    expect(page.get_by_role("button", name="Random song")).to_be_disabled()


def test_floating_buttons_stay_clear_of_the_search_bar(page, library, make_song):
    """Back to top hangs under the sticky title, Scroll down sits in the bottom corner, and none covers another."""
    long = open_long_song(page, library, make_song)
    page.evaluate("scrollTo(0, 1000)")
    boxes = {
        name: page.get_by_role("button", name=name).bounding_box()
        for name in ("Random song", "Back to top", "Scroll down")
    }
    title = long.locator("summary").bounding_box()

    def overlap(one, other):
        return (
            one["x"] < other["x"] + other["width"]
            and other["x"] < one["x"] + one["width"]
            and (one["y"] < other["y"] + other["height"] and other["y"] < one["y"] + one["height"])
        )

    viewport = page.viewport_size
    for name, box in boxes.items():
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"], name
        assert box["y"] >= 0 and box["y"] + box["height"] <= viewport["height"], name
    assert boxes["Back to top"]["y"] >= title["y"] + title["height"]
    assert not overlap(boxes["Random song"], boxes["Back to top"])
    assert not overlap(boxes["Random song"], boxes["Scroll down"])
    assert not overlap(boxes["Back to top"], boxes["Scroll down"])


def test_back_to_top_stays_put_when_scroll_down_goes_away(page, library, make_song):
    """Back to top keeps its place at the top when Scroll down hides at the end of the song."""
    open_long_song(page, library, make_song)
    page.evaluate("scrollTo(0, 1000)")
    to_top = page.get_by_role("button", name="Back to top")
    before = to_top.bounding_box()

    page.evaluate("scrollTo(0, document.documentElement.scrollHeight)")

    expect(page.get_by_role("button", name="Scroll down")).to_have_count(0)
    assert to_top.bounding_box() == before


def test_capo_and_video_link_are_shown(page, library):
    """Songs with a capo or a link say so."""
    page.goto("/categories/cs")

    songs(page).nth(2).locator("summary").click()

    expect(page.get_by_text("Capo 2")).to_be_visible()
    expect(page.get_by_title("YouTube")).to_have_attribute("href", "https://example.com/v")


def test_transposing_changes_the_chords(page, library):
    """Czech names: H is the natural B, so one up from H is C."""
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()
    chords = songs(page).nth(0).locator(".chord")
    expect(chords).to_have_text(["Ami", "C", "H", "Emi"])

    page.get_by_role("button", name="Transpose +1").click()
    expect(chords).to_have_text(["A#mi", "C#", "C", "Fmi"])

    page.get_by_role("button", name="Transpose −1").click()
    page.get_by_role("button", name="Transpose −1").click()
    expect(chords).to_have_text(["G#mi", "H", "A#", "D#mi"])


def test_chords_stand_above_the_text(page, library):
    """By default the chords are annotations over their words."""
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()
    chords = songs(page).nth(0).locator("rt.chord")
    expect(chords).to_have_count(4)

    above = chords.first.evaluate(
        "rt => rt.getBoundingClientRect().bottom <= rt.parentElement.getBoundingClientRect().bottom - 10"
    )
    assert above


def test_chords_can_stay_in_the_line(page, library, settings):
    """The inline renderer keeps the chords in the line of text."""
    settings.SONG_RENDERER = "chords.markdown.INLINE_RENDERER"
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()

    expect(songs(page).nth(0).locator("span.chord")).to_have_text(["Ami", "C", "H", "Emi"])
    expect(songs(page).nth(0).locator("ruby")).to_have_count(0)


def test_transposing_starts_again_for_the_next_song(page, library):
    """The shift belongs to the open song."""
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()
    page.get_by_role("button", name="Transpose +1").click()

    songs(page).nth(1).locator("summary").click()

    expect(songs(page).nth(1).locator(".chord")).to_have_text(["G", "D"])


def test_hide_chords_option_is_remembered(page, library):
    """Chords can be hidden and the choice survives a reload."""
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()
    open_menu(page, "Options")

    page.get_by_label("Hide chords").check()

    expect(songs(page).nth(0).locator(".chord").first).to_be_hidden()
    page.reload()
    songs(page).nth(0).locator("summary").click()
    expect(songs(page).nth(0).locator(".chord").first).to_be_hidden()


def test_columns_option_is_remembered(page, library):
    """The number of columns is a CSS variable and survives a reload."""
    page.goto("/categories/cs")
    open_menu(page, "Options")

    page.get_by_label("Columns").fill("3")

    expect(page.locator("html")).to_have_css("--chords-grid-columns", "3")
    page.reload()
    expect(page.locator("html")).to_have_css("--chords-grid-columns", "3")


@pytest.mark.parametrize(
    ("stored", "width", "columns"),
    [
        pytest.param(None, 375, "1", id="phone"),
        pytest.param(None, 1280, "2", id="laptop"),
        pytest.param(None, 1920, "3", id="wide screen"),
        pytest.param("1", 1920, "1", id="chosen"),
    ],
)
def test_columns_default_to_the_width_of_the_screen(page, library, stored, width, columns):
    """Until the reader chooses, wider screens get more columns; a stored choice is kept whatever the screen."""
    if stored:
        page.add_init_script(f"localStorage.setItem('columns', '{stored}')")
    page.set_viewport_size({"width": width, "height": 800})
    page.goto("/categories/cs")

    expect(page.locator("html")).to_have_css("--chords-grid-columns", columns)


def test_short_song_gets_no_empty_columns(page, library):
    """A song of two verses fills two of three columns, and both start at the same height."""
    page.add_init_script("localStorage.setItem('columns', '3')")
    page.emulate_media(reduced_motion="reduce")
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()
    text = songs(page).nth(0).locator(".song-text")
    expect(text.locator("p")).to_have_count(2)

    expect(text).to_have_css("column-count", "2")
    tops = text.locator("p").evaluate_all("verses => verses.map(verse => verse.getBoundingClientRect().top)")
    assert tops[0] == tops[1]


def test_theme_is_applied_and_remembered(page, library):
    """The dark theme sets the attribute and keeps the key the old pages used."""
    page.goto("/categories/cs")
    open_menu(page, "Options")

    page.get_by_role("button", name="Dark").click()

    expect(page.locator("html")).to_have_attribute("data-bs-theme", "dark")
    assert page.evaluate("localStorage.getItem('theme')") == "dark"
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-bs-theme", "dark")


def test_language_can_be_switched(page, library):
    """The interface changes language at once and remembers it."""
    page.goto("/categories/cs")
    expect(page.get_by_label("Search")).to_be_visible()
    open_menu(page, "Options")

    page.get_by_label("Language").select_option("cs")

    expect(page.get_by_label("Vyhledávání")).to_be_visible()
    expect(page.locator("html")).to_have_attribute("lang", "cs")
    page.reload()
    expect(page.get_by_label("Vyhledávání")).to_be_visible()


def test_dropdown_closes_on_escape_and_outside_click(page, library):
    """Only one menu is open and it goes away when asked."""
    page.goto("/categories/cs")
    open_menu(page, "Options")
    expect(page.locator("details.sb-dd[open]")).to_have_count(1)

    page.keyboard.press("Escape")
    expect(page.locator("details.sb-dd[open]")).to_have_count(0)

    open_menu(page, "Categories")
    page.get_by_label("Search").click()
    expect(page.locator("details.sb-dd[open]")).to_have_count(0)


def test_qr_code_dialog(page, library):
    """The QR code of the current address opens in a dialog."""
    page.goto("/categories/cs")

    page.get_by_role("button", name="QR code").click()

    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_role("img")).to_be_visible()
    expect(dialog.get_by_role("link")).to_have_text(page.url)
    dialog.get_by_role("button", name="Close").click()
    expect(dialog).to_be_hidden()


def test_menu_lists_links_and_pdfs_only_when_there_are_some(page, library):
    """Dropdowns without content are not drawn."""
    page.goto("/categories/cs")

    expect(page.locator("summary", has_text="See also")).to_have_count(0)
    expect(page.locator("summary", has_text="PDF")).to_have_count(0)


def test_messages_of_the_server_are_shown(page, library):
    """Messages that waited for the reader appear as a notice."""
    page.route(
        "**/api/me",
        lambda route: route.fulfill(
            content_type="application/json",
            body=json.dumps(
                {
                    "auth": False,
                    "username": None,
                    "localadmin": False,
                    "superuser": False,
                    "messages": [{"level": "success", "text": "Song saved"}],
                }
            ),
        ),
    )

    page.goto("/categories/cs")

    expect(page.get_by_role("status").get_by_text("Song saved")).to_be_visible()


def test_data_failure_offers_a_retry(page, library):
    """A first visit that cannot load the songs says so and can try again."""
    page.route("**/api/songs", lambda route: route.abort())
    page.goto("/categories/cs")
    expect(page.get_by_text("The songs could not be loaded")).to_be_visible()

    page.unroute("**/api/songs")
    page.get_by_role("button", name="Try again").click()

    expect(songs(page)).to_have_count(3)


def test_only_the_changed_song_is_downloaded(page, library):
    """A returning reader asks for what changed since its copy, and gets the edit and an added song merged in."""
    for category in library.category_set.all():
        category.song_set.update(updated_at="2020-01-01T00:00:00Z")
    page.goto("/categories/cs")
    expect(songs(page)).to_have_count(3)
    page.wait_for_load_state("networkidle")  # the in-memory database is locked while the server reads it
    category = library.category_set.get(slug="cs")
    song = category.song_set.get(name="Hrad")
    song.name = "Hrad Karlštejn"
    song.save()
    category.song_set.create(name="Nová", text="text")

    changed = []

    def record(route):
        # the browser drops the body of a streamed response, so fetch it here and hand it on
        response = route.fetch()
        changed.append(len(response.json()["changed"]))
        route.fulfill(response=response)

    page.route(lambda url: "since=" in url, record)
    page.reload()

    expect(songs(page)).to_have_count(4)
    expect(page.locator("details.song > summary").nth(1)).to_contain_text("Hrad Karlštejn")
    assert changed == [2]


def test_songs_are_kept_for_offline_use(page, context, library):
    """After one visit the reader opens without any connection."""
    page.goto("/categories/cs")
    expect(songs(page)).to_have_count(3)
    page.evaluate("navigator.serviceWorker.ready")
    page.wait_for_function("caches.open('songs').then(cache => cache.keys()).then(keys => keys.length > 0)")

    context.set_offline(True)
    page.reload()

    expect(songs(page)).to_have_count(3)
    go_to_category(page, "English")
    expect(songs(page)).to_have_count(2)
    page.goto("/categories/en")
    expect(songs(page)).to_have_count(2)


def test_admin_sees_edit_links_and_can_log_out(page, context, library, staff_user, sign_in):
    """Tenant administrators get edit and delete links; logging out forgets them and the stored songs."""
    sign_in(staff_user)
    page.goto("/categories/cs")
    open_menu(page, "Account")
    expect(page.get_by_text("Logged in as")).to_contain_text("staff")
    song = library.category_set.get(slug="cs").song_set.get(name="Hrad")

    page.keyboard.press("Escape")
    songs(page).nth(1).locator("summary").click()
    edit = page.get_by_role("link", name="Edit")
    expect(edit).to_have_attribute("href", f"/edit/{song.id}?next=%2Fcategories%2Fcs")
    expect(page.get_by_role("link", name="Delete")).to_have_attribute(
        "href", f"/delete/{song.id}?next=%2Fcategories%2Fcs"
    )

    open_menu(page, "Account")
    page.get_by_role("button", name="Log out").click()

    expect(page.get_by_role("link", name="Log in")).to_be_visible()
    expect(page.get_by_role("link", name="Edit")).to_have_count(0)


def test_superuser_sees_archived_songs_until_logout(page, library, superuser, sign_in):
    """Archived songs come with the superuser's list and are gone with the session."""
    sign_in(superuser)
    page.goto("/categories/cs")

    expect(songs(page)).to_have_count(4)
    expect(page.locator("details.song.archived")).to_have_count(1)
    expect(page.locator("summary", has_text="Admin")).to_be_visible()

    open_menu(page, "Account")
    page.route("**/api/songs", lambda route: route.abort())
    page.get_by_role("button", name="Log out").click()

    # with the network gone only a stored list could be shown, and none is left
    expect(page.get_by_text("The songs could not be loaded")).to_be_visible()
    expect(page.locator("details.song.archived")).to_have_count(0)


def test_anonymous_visitor_has_no_admin_menu(page, library):
    """Nothing administrative is drawn for the public."""
    page.goto("/categories/cs")

    expect(page.get_by_role("link", name="Log in")).to_have_attribute(
        "href", "/accounts/login/?next=%2Fcategories%2Fcs"
    )
    expect(page.locator("summary", has_text="Admin")).to_have_count(0)


def shell_caches(page):
    """Returns the names of the shell caches of the service worker."""
    return page.evaluate("caches.keys().then(names => names.filter(name => name.startsWith('shell-')))")


def test_new_version_is_offered_and_installed_on_request(page, library, monkeypatch):
    """A changed worker waits until the reader agrees to reload, then replaces the old caches."""
    page.goto("/categories/cs")
    page.evaluate("navigator.serviceWorker.ready")
    page.reload()
    expect(songs(page)).to_have_count(3)
    page.wait_for_function("navigator.serviceWorker.controller !== null")
    before = shell_caches(page)
    assert len(before) == 1

    monkeypatch.setattr("frontend.views.ASSETS", [*ASSETS, "styles.css"])
    page.evaluate("navigator.serviceWorker.getRegistration().then(registration => registration.update())")

    expect(page.get_by_text("A new version is available")).to_be_visible()
    expect(songs(page)).to_have_count(3)
    assert set(before) < set(shell_caches(page))
    with page.expect_navigation():
        page.get_by_role("button", name="Reload").click()

    expect(songs(page)).to_have_count(3)
    page.wait_for_function("caches.keys().then(names => names.filter(name => name.startsWith('shell-')).length === 1)")
    assert set(shell_caches(page)).isdisjoint(before)


def test_edited_file_is_offered_as_a_new_version_in_development(page, library, settings, monkeypatch, tmp_path):
    """With static files unhashed, changing a reader file still makes the browser offer the update."""
    settings.DEBUG = True
    stylesheet = tmp_path / "header.css"
    stylesheet.write_text(Path(finders.find("app/header.css")).read_text())
    find = finders.find
    monkeypatch.setattr(
        "frontend.views.finders.find", lambda path: stylesheet if path == "app/header.css" else find(path)
    )
    page.goto("/categories/cs")
    page.evaluate("navigator.serviceWorker.ready")
    page.reload()
    expect(songs(page)).to_have_count(3)
    page.wait_for_function("navigator.serviceWorker.controller !== null")

    stylesheet.write_text(stylesheet.read_text() + "\n/* edited */\n")
    page.reload()

    expect(page.get_by_text("A new version is available")).to_be_visible()
