"""Browser tests of the server pages whose content is drawn by the client."""

import json

import pytest
from django.urls import reverse
from playwright.sync_api import expect


@pytest.fixture(autouse=True)
def offline_cdn(page):
    """Bootstrap comes from a CDN; the pages do not need it, so tests do not wait for it"""
    page.route("https://cdn.jsdelivr.net/**", lambda route: route.fulfill(body="", content_type="text/plain"))


@pytest.fixture
def render_info(page):
    """Answers the progress page's polling with the given states, the last one for good"""
    states = []

    def answer(route):
        state = states.pop(0) if len(states) > 1 else states[0]
        route.fulfill(body=json.dumps(state), content_type="application/json")

    page.route("**/pdf/files/info/*", answer)
    return states


def info(progress=0, ready=False, failed=False, link=None):
    return {"ready": ready, "failed": failed, "progress": progress, "link": link, "scheduled_at": None}


def test_progress_follows_the_render(page, library, pdf_file, render_info):
    """The steps of the render are shown until the finished file can be downloaded"""
    render_info.extend([info(), info(progress=2), info(progress=7, ready=True, link="/media/songbook.pdf")])

    page.goto(reverse("pdf:files:wait", kwargs={"pk": pdf_file.pk}))

    expect(page.get_by_text("songbook.pdf", exact=True)).to_be_visible()
    expect(page.get_by_role("status").filter(has_text="Completed")).to_be_visible()
    expect(page.get_by_role("link", name="/media/songbook.pdf")).to_have_attribute("href", "/media/songbook.pdf")
    expect(page.get_by_role("progressbar")).to_have_attribute("aria-valuenow", "100")


def test_progress_reports_a_failed_render(page, library, pdf_file, render_info):
    """A render that failed is not polled for ever"""
    render_info.append(info(progress=3, failed=True))

    page.goto(reverse("pdf:files:wait", kwargs={"pk": pdf_file.pk}))

    expect(page.get_by_role("status").filter(has_text="Failed")).to_be_visible()
    expect(page.get_by_role("link", name="Back to all files")).to_be_visible()


def test_progress_is_polled_from_the_server(page, library, pdf_file):
    """Without stubs the page shows what the server reports about a queued file"""
    page.goto(reverse("pdf:files:wait", kwargs={"pk": pdf_file.pk}))

    expect(page.get_by_role("status").filter(has_text="Waiting for start")).to_be_visible()
    expect(page.get_by_role("progressbar")).to_have_attribute("aria-valuenow", "0")
