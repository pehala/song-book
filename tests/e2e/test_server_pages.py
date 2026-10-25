"""Browser tests of the header on the pages the server renders with Bootstrap."""

import pytest
from playwright.sync_api import expect


@pytest.fixture(autouse=True)
def offline_cdn(page):
    """Bootstrap comes from a CDN; the header does not need it, so tests do not wait for it"""
    page.route("https://cdn.jsdelivr.net/**", lambda route: route.fulfill(body="", content_type="text/plain"))


def has_language_cookie(page):
    return any(cookie["name"] == "django_language" for cookie in page.context.cookies())


def wait_for_language_cookie(page):
    """The server sets the cookie in the answer to a POST the page sends in the background"""
    for _ in range(50):
        if has_language_cookie(page):
            return
        page.wait_for_timeout(100)


def labels(page):
    return page.locator("header.sb-bar summary, header.sb-bar nav > a, header.sb-bar nav > button").all_inner_texts()


def test_server_page_has_the_readers_header(page, library, staff_user, sign_in):
    """An administrative page offers the same menus as the reader, for the same user"""
    sign_in(staff_user)
    page.goto("/categories/cs")
    expect(page.locator("summary", has_text="Account")).to_be_visible()
    reader = labels(page)

    page.goto("/categories/")
    expect(page.locator("summary", has_text="Account")).to_be_visible()

    assert labels(page) == reader


def test_server_page_header_knows_the_user(page, library, staff_user, sign_in):
    """The account menu names the signed in user without a request to the API"""
    sign_in(staff_user)
    page.goto("/categories/")

    page.locator("summary", has_text="Account").click()

    expect(page.get_by_text("Logged in as")).to_contain_text("staff")


def test_anonymous_server_page_offers_login(page, library):
    """The login page's header has a login link"""
    page.goto("/accounts/login/")

    expect(page.get_by_role("link", name="Log in").first).to_be_visible()


def test_category_link_leaves_for_the_reader(page, library, staff_user, sign_in):
    """From an administrative page the categories are ordinary links into the reader"""
    sign_in(staff_user)
    page.goto("/categories/")

    page.locator("summary", has_text="Categories").click()
    page.locator("header.sb-bar").get_by_role("link", name="English").click()

    expect(page).to_have_url(f"{page.url.split('/categories')[0]}/categories/en")
    expect(page.locator("details.song")).to_have_count(2)


def test_theme_choice_is_shared_with_bootstrap(page, library):
    """The attribute Bootstrap reads follows the header's theme buttons and the reader's choice"""
    page.goto("/categories/cs")
    page.locator("summary", has_text="Options").click()
    page.get_by_role("button", name="Dark").click()

    page.goto("/accounts/login/")
    expect(page.locator("html")).to_have_attribute("data-bs-theme", "dark")

    page.locator("summary", has_text="Options").click()
    page.get_by_role("button", name="Light").click()
    expect(page.locator("html")).to_have_attribute("data-bs-theme", "light")


def test_language_is_changed_by_the_server(page, library):
    """A language picked in the header reloads the page in that language"""
    page.goto("/accounts/login/")
    page.locator("summary", has_text="Options").click()

    page.get_by_label("Language").select_option("cs")

    expect(page.locator("html")).to_have_attribute("lang", "cs")
    expect(page.locator("summary", has_text="Možnosti")).to_be_visible()


def test_options_of_the_reader_are_left_out(page, library):
    """Columns, chords and wake lock mean nothing without songs"""
    page.goto("/accounts/login/")
    page.locator("summary", has_text="Options").click()

    expect(page.get_by_label("Columns")).to_have_count(0)
    expect(page.get_by_label("Hide chords")).to_have_count(0)


def test_reader_follows_the_language_the_server_chose(page, context, library, live_server):
    """The cookie of the Django pages wins over what the reader stored earlier"""
    context.add_cookies([{"name": "django_language", "value": "cs", "url": live_server.url}])
    page.add_init_script("localStorage.setItem('lang', 'en')")

    page.goto("/categories/cs")

    expect(page.get_by_label("Vyhledávání")).to_be_visible()


def test_language_chosen_in_the_reader_reaches_server_pages(page, library):
    """Picking a language in the reader sets the cookie the Django pages read"""
    page.goto("/categories/cs")
    page.locator("summary", has_text="Options").click()
    page.get_by_label("Language").select_option("cs")
    expect(page.get_by_label("Vyhledávání")).to_be_visible()
    wait_for_language_cookie(page)

    page.goto("/accounts/login/")

    expect(page.locator("html")).to_have_attribute("lang", "cs")
    expect(page.locator("summary", has_text="Možnosti")).to_be_visible()


def test_language_chosen_before_the_user_is_known_reaches_server_pages(page, library):
    """The CSRF cookie comes with /api/me, so a language picked before it answered waits for it"""
    held = []

    def hold(route):  # Playwright cannot wrap the builtin held.append
        held.append(route)

    page.route("**/api/me", hold)
    page.goto("/categories/cs")
    page.locator("summary", has_text="Options").click()
    page.get_by_label("Language").select_option("cs")
    expect(page.get_by_label("Vyhledávání")).to_be_visible()
    assert not has_language_cookie(page)

    held[0].continue_()
    wait_for_language_cookie(page)

    page.goto("/accounts/login/")
    expect(page.locator("html")).to_have_attribute("lang", "cs")
