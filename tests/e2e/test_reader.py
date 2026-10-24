"""Browser tests of the reader: routing, search, song view, options and the service worker."""

import json
from pathlib import Path
from urllib.parse import urlsplit

from django.contrib.staticfiles import finders
from playwright.sync_api import expect

from analytics.models import DayStatistic
from frontend.views import ASSETS


def songs(page):
    return page.locator("details.song")


def titles(page):
    return page.locator("details.song h2")


def numbers(page):
    return page.locator("details.song .num")


def open_menu(page, name):
    page.locator("summary", has_text=name).click()


def go_to_category(page, name):
    open_menu(page, "Categories")
    page.get_by_role("link", name=name).click()


def test_landing_page_is_drawn_from_the_shell(page, library):
    """/ shows the tenant's landing page without a redirect from the server"""
    page.goto("/")

    expect(page).to_have_url(page.url.split("/", 3)[0] + "//" + urlsplit(page.url).netloc + "/categories/cs")
    expect(songs(page)).to_have_count(3)
    expect(page.locator("header .sb-brand")).to_have_text(library.display_name)
    expect(page).to_have_title(f"Česky | {library.display_name}")


def test_songs_are_numbered_and_archived_ones_hidden(page, library):
    """Anonymous visitors see the public songs of the category, numbered from 1"""
    page.goto("/categories/cs")

    expect(numbers(page)).to_have_text(["1.", "2.", "3."])
    expect(titles(page)).to_have_text(["Jožin z bažin", "Hrad", "Both Songs"])


def test_all_songs_lists_every_song(page, library):
    """The all songs route shows what is in every category"""
    page.goto("/all")

    expect(songs(page)).to_have_count(4)


def test_shell_placeholder_is_gone_once_the_reader_is_drawn(page, library):
    """The spinner of the shell must not linger below the song list"""
    page.goto("/all")

    expect(songs(page)).to_have_count(4)
    expect(page.locator(".spinner")).to_have_count(0)


def test_switching_category_asks_the_server_for_nothing(page, library, requests_made):
    """The songs are held already, so changing category is a pushState and a filter"""
    page.goto("/categories/cs")
    expect(songs(page)).to_have_count(3)
    seen = len(requests_made)

    go_to_category(page, "English")

    expect(page).to_have_url(f"{urlsplit(page.url).scheme}://{urlsplit(page.url).netloc}/categories/en")
    expect(titles(page)).to_have_text(["Both Songs", "Amazing Grace"])
    assert [url for _, url in requests_made[seen:] if "/api/songs" in url or url.endswith("/categories/en")] == []


def test_back_button_returns_to_the_previous_category(page, library):
    """Client-side routes live in the history"""
    page.goto("/categories/cs")
    go_to_category(page, "English")
    expect(songs(page)).to_have_count(2)

    page.go_back()

    expect(songs(page)).to_have_count(3)


def test_unknown_category_says_so(page, library):
    """A slug nobody owns is explained, not left blank"""
    page.goto("/categories/nope")

    expect(page.get_by_text("This category does not exist.")).to_be_visible()


def test_everything_comes_from_one_origin(page, library, requests_made):
    """No CDN: the reader works on a connection that can reach nothing else"""
    page.goto("/categories/cs")
    expect(songs(page)).to_have_count(3)

    origins = {urlsplit(url).netloc for _, url in requests_made}

    assert origins == {urlsplit(page.url).netloc}


def test_search_ignores_case_and_diacritics(page, library):
    """Typing 'jozin' finds 'Jožin'"""
    page.goto("/categories/cs")

    page.get_by_label("Search").fill("JOZIN")

    expect(titles(page)).to_have_text(["Jožin z bažin"])


def test_search_looks_into_the_text_and_the_author(page, library):
    """Lyrics and authors are searched, chords are part of the text"""
    page.goto("/categories/cs")
    search = page.get_by_label("Search")

    search.fill("stojí hrad")
    expect(songs(page)).to_have_count(1)
    search.fill("mládek")
    expect(titles(page)).to_have_text(["Jožin z bažin"])


def test_search_terms_separated_by_semicolon_all_have_to_match(page, library):
    """`a;b` means both a and b"""
    page.goto("/categories/cs")
    search = page.get_by_label("Search")

    search.fill("jedu;lesem")
    expect(songs(page)).to_have_count(1)
    search.fill("jedu;hrad")
    expect(page.get_by_text("No songs found")).to_be_visible()


def test_search_matches_the_number_of_the_list(page, library):
    """The numbers shown are searchable, and they follow the route"""
    page.goto("/categories/en")

    page.get_by_label("Search").fill("2")

    expect(numbers(page)).to_have_text(["2."])
    expect(titles(page)).to_have_text(["Amazing Grace"])


def test_opening_a_song_shows_its_text(page, library):
    """The body is drawn when the song is opened"""
    page.goto("/categories/cs")

    songs(page).nth(1).locator("summary").click()

    expect(songs(page).nth(1).locator(".song-text")).to_contain_text("stojí hrad")


def test_one_song_is_open_at_a_time(page, library):
    """Opening a song closes the previous one"""
    page.goto("/categories/cs")

    songs(page).nth(0).locator("summary").click()
    songs(page).nth(1).locator("summary").click()

    expect(page.locator("details.song[open]")).to_have_count(1)
    expect(songs(page).nth(1)).to_have_attribute("open", "")


def test_capo_and_video_link_are_shown(page, library):
    """Songs with a capo or a link say so"""
    page.goto("/categories/cs")

    songs(page).nth(2).locator("summary").click()

    expect(page.get_by_text("Capo 2")).to_be_visible()
    expect(page.get_by_title("YouTube")).to_have_attribute("href", "https://example.com/v")


def test_transposing_changes_the_chords(page, library):
    """Czech names: H is the natural B, so one up from H is C"""
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()
    chords = songs(page).nth(0).locator(".chord")
    expect(chords).to_have_text(["Ami", "C", "H", "Emi"])

    page.get_by_role("button", name="Transpose +1").click()
    expect(chords).to_have_text(["A#mi", "C#", "C", "Fmi"])

    page.get_by_role("button", name="Transpose −1").click()
    page.get_by_role("button", name="Transpose −1").click()
    expect(chords).to_have_text(["G#mi", "H", "A#", "D#mi"])


def test_chords_can_stand_above_the_text(page, library, settings):
    """With the above renderer the chords are annotations over their words and still transpose"""
    settings.SONG_RENDERER = "chords.markdown.RUBY_RENDERER"
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()
    chords = songs(page).nth(0).locator("rt.chord")
    expect(chords).to_have_text(["Ami", "C", "H", "Emi"])
    above = chords.first.evaluate(
        "rt => rt.getBoundingClientRect().bottom <= rt.parentElement.getBoundingClientRect().bottom - 10"
    )
    assert above

    page.get_by_role("button", name="Transpose +1").click()

    expect(chords).to_have_text(["A#mi", "C#", "C", "Fmi"])


def test_transposing_starts_again_for_the_next_song(page, library):
    """The shift belongs to the open song"""
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()
    page.get_by_role("button", name="Transpose +1").click()

    songs(page).nth(1).locator("summary").click()

    expect(songs(page).nth(1).locator(".chord")).to_have_text(["G", "D"])


def test_hide_chords_option_is_remembered(page, library):
    """Chords can be hidden and the choice survives a reload"""
    page.goto("/categories/cs")
    songs(page).nth(0).locator("summary").click()
    open_menu(page, "Options")

    page.get_by_label("Hide chords").check()

    expect(songs(page).nth(0).locator(".chord").first).to_be_hidden()
    page.reload()
    songs(page).nth(0).locator("summary").click()
    expect(songs(page).nth(0).locator(".chord").first).to_be_hidden()


def test_columns_option_is_remembered(page, library):
    """The number of columns is a CSS variable and survives a reload"""
    page.goto("/categories/cs")
    open_menu(page, "Options")

    page.get_by_label("Columns").fill("3")

    expect(page.locator("html")).to_have_css("--chords-grid-columns", "3")
    page.reload()
    expect(page.locator("html")).to_have_css("--chords-grid-columns", "3")


def test_theme_is_applied_and_remembered(page, library):
    """The dark theme sets the attribute and keeps the key the old pages used"""
    page.goto("/categories/cs")
    open_menu(page, "Options")

    page.get_by_role("button", name="Dark").click()

    expect(page.locator("html")).to_have_attribute("data-bs-theme", "dark")
    assert page.evaluate("localStorage.getItem('theme')") == "dark"
    page.reload()
    expect(page.locator("html")).to_have_attribute("data-bs-theme", "dark")


def test_language_can_be_switched(page, library):
    """The interface changes language at once and remembers it"""
    page.goto("/categories/cs")
    expect(page.get_by_label("Search")).to_be_visible()
    open_menu(page, "Options")

    page.get_by_label("Language").select_option("cs")

    expect(page.get_by_label("Vyhledávání")).to_be_visible()
    expect(page.locator("html")).to_have_attribute("lang", "cs")
    page.reload()
    expect(page.get_by_label("Vyhledávání")).to_be_visible()


def test_dropdown_closes_on_escape_and_outside_click(page, library):
    """Only one menu is open and it goes away when asked"""
    page.goto("/categories/cs")
    open_menu(page, "Options")
    expect(page.locator("details.sb-dd[open]")).to_have_count(1)

    page.keyboard.press("Escape")
    expect(page.locator("details.sb-dd[open]")).to_have_count(0)

    open_menu(page, "Categories")
    page.get_by_label("Search").click()
    expect(page.locator("details.sb-dd[open]")).to_have_count(0)


def test_qr_code_dialog(page, library):
    """The QR code of the current address opens in a dialog"""
    page.goto("/categories/cs")

    page.get_by_role("button", name="QR").click()

    dialog = page.get_by_role("dialog")
    expect(dialog.get_by_role("img")).to_be_visible()
    expect(dialog.get_by_role("link")).to_have_text(page.url)
    dialog.get_by_role("button", name="Close").click()
    expect(dialog).to_be_hidden()


def test_menu_lists_links_and_pdfs_only_when_there_are_some(page, library):
    """Dropdowns without content are not drawn"""
    page.goto("/categories/cs")

    expect(page.locator("summary", has_text="See also")).to_have_count(0)
    expect(page.locator("summary", has_text="PDF")).to_have_count(0)


def recorded_hits(page, key):
    """The hits of a key, once the beacon has arrived"""
    for _ in range(50):
        statistic = DayStatistic.objects.filter(key=key).first()
        if statistic:
            return statistic.hits
        page.wait_for_timeout(100)
    return 0


def test_visits_are_counted(page, library):
    """Each route drawn reports itself to the statistics"""
    page.goto("/categories/cs")
    expect(songs(page)).to_have_count(3)
    go_to_category(page, "English")
    expect(songs(page)).to_have_count(2)

    assert recorded_hits(page, "cs") == 1
    assert recorded_hits(page, "en") == 1


def test_messages_of_the_server_are_shown(page, library):
    """Messages that waited for the reader appear as a notice"""
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
    """A first visit that cannot load the songs says so and can try again"""
    page.route("**/api/songs", lambda route: route.abort())
    page.goto("/categories/cs")
    expect(page.get_by_text("The songs could not be loaded")).to_be_visible()

    page.unroute("**/api/songs")
    page.get_by_role("button", name="Try again").click()

    expect(songs(page)).to_have_count(3)


def test_changed_songs_replace_the_stored_ones(page, library):
    """A returning reader gets the edit on the next visit"""
    page.goto("/categories/cs")
    expect(songs(page)).to_have_count(3)
    page.wait_for_load_state("networkidle")  # the in-memory database is locked while the server reads it
    song = library.category_set.get(slug="cs").song_set.get(name="Hrad")

    song.name = "Hrad Karlštejn"
    song.save()
    page.reload()

    expect(page.locator("details.song > summary").nth(1)).to_contain_text("Hrad Karlštejn")


def test_only_the_changed_song_is_downloaded(page, library):
    """A returning reader asks for what changed since its copy, and gets the edit and an added song merged in"""
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

    bodies = []
    page.on("response", lambda response: bodies.append(response) if "since=" in response.url else None)
    page.reload()

    expect(songs(page)).to_have_count(4)
    expect(page.locator("details.song > summary").nth(1)).to_contain_text("Hrad Karlštejn")
    assert [len(response.json()["changed"]) for response in bodies] == [2]


def test_songs_are_kept_for_offline_use(page, context, library):
    """After one visit the reader opens without any connection"""
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
    """Tenant administrators get edit and delete links; logging out forgets them and the stored songs"""
    sign_in(staff_user)
    page.goto("/categories/cs")
    open_menu(page, "Account")
    expect(page.get_by_text("Logged as")).to_contain_text("staff")
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
    """Archived songs come with the superuser's list and are gone with the session"""
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
    """Nothing administrative is drawn for the public"""
    page.goto("/categories/cs")

    expect(page.get_by_role("link", name="Log in")).to_have_attribute(
        "href", "/accounts/login/?next=%2Fcategories%2Fcs"
    )
    expect(page.locator("summary", has_text="Admin")).to_have_count(0)


def shell_caches(page):
    return page.evaluate("caches.keys().then(names => names.filter(name => name.startsWith('shell-')))")


def test_new_version_is_offered_and_installed_on_request(page, library, monkeypatch):
    """A changed worker waits until the reader agrees to reload, then replaces the old caches"""
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
    """With static files unhashed, changing a reader file still makes the browser offer the update"""
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
