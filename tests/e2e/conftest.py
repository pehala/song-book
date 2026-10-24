"""Fixtures for the browser tests of the reader.

They drive a real Chromium against Django's live server, so they need the browser installed
(`uv run playwright install --with-deps chromium`) and are left out of the default test run;
`make e2e` runs them.
"""

import os

import pytest
from django.test import Client

# Playwright's sync API runs an event loop in the test thread, which Django refuses to query from
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


def pytest_collection_modifyitems(items):
    """Marks everything under tests/e2e so the default run can leave it out"""
    for item in items:
        if "/tests/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture(scope="session")
def base_url(live_server):
    return live_server.url


@pytest.fixture
def browser_context_args(browser_context_args):
    """Readers are English unless a test says otherwise"""
    return {**browser_context_args, "locale": "en-US"}


@pytest.fixture
def library(tenant, make_category, make_song):
    """A songbook with two categories, a song in both of them and a hidden one"""
    tenant.category_set.all().delete()
    tenant.index_redirect = "/categories/cs"
    tenant.save()
    cs = make_category(tenant, name="Česky", slug="cs")
    en = make_category(tenant, name="English", slug="en")
    make_song(
        cs, name="Jožin z bažin", author="Ivan Mládek", text="{Ami}Jedu takhle {C}lesem\n\n{H}Druhý {Emi}odstavec"
    )
    make_song(cs, name="Hrad", author="Karel", text="{G}Na vrchu {D}stojí hrad")
    make_song(cs, en, name="Both Songs", author="Anon", text="{C}Sung in {G}both", capo=2, link="https://example.com/v")
    make_song(en, name="Amazing Grace", author="John Newton", text="{G}Amazing grace how {D}sweet")
    make_song(cs, name="Secret", text="{C}Hidden", archived=True)
    return tenant


@pytest.fixture
def sign_in(context, live_server):
    """Signs the browser in as the given user"""

    def sign_in(user):
        client = Client()
        client.force_login(user)
        context.add_cookies([{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}])

    return sign_in


@pytest.fixture
def requests_made(page):
    """Every request the page makes, as (method, url) pairs"""
    made = []
    page.on("request", lambda request: made.append((request.method, request.url)))
    return made
