"""Tests for the page every reader route is served with."""

import json
import re

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from frontend.views import MODULES
from tenants.bootstrap import bootstrap_payload

pytestmark = pytest.mark.django_db


def boot_of(response):
    """The bootstrap JSON inlined into the page."""
    return json.loads(
        re.search(r'<script id="boot" type="application/json">(.*?)</script>', response.content.decode()).group(1)
    )


@pytest.fixture
def shell_urls(category):
    """The URLs that are answered with the shell."""
    return ["/", reverse("chords:all"), reverse("category:index", kwargs={"slug": category.slug})]


def test_index_is_the_shell_not_a_redirect(anon_client, tenant):
    """The reader moves to the landing page itself, which saves a round trip."""
    response = anon_client.get(reverse("chords:index"))

    assert response.status_code == 200
    assert 'id="app"' in response.content.decode()


def test_every_reader_route_serves_the_same_page(anon_client, shell_urls):
    """The service worker keeps a single copy for all of them."""
    bodies = {anon_client.get(url).content for url in shell_urls}

    assert len(bodies) == 1


def test_page_carries_the_bootstrap(anon_client, tenant, category):
    """Navigation and urls are inlined so the first draw needs no request."""
    boot = boot_of(anon_client.get(reverse("chords:all")))

    assert boot == json.loads(json.dumps(bootstrap_payload(tenant)))


def test_page_carries_no_songs(anon_client, song):
    """The songs are fetched from /api/songs."""
    assert song.name not in anon_client.get(reverse("chords:all")).content.decode()


def test_page_preloads_modules_but_not_songs(anon_client, tenant):
    """The modules are requested in a single round trip; the songs are not, the reader may ask for a delta."""
    html = anon_client.get(reverse("chords:all")).content.decode()

    for module in MODULES:
        assert f'<link rel="modulepreload" href="/static/{module}">' in html
    assert '<link rel="stylesheet" href="/static/app/header.css">' in html
    assert '<link rel="stylesheet" href="/static/app/app.css">' in html
    assert 'rel="preload"' not in html
    assert f'<script type="module" src="/static/{MODULES[0]}"></script>' in html


def test_page_links_the_manifest(anon_client, tenant):
    """The browser can offer to install the songbook."""
    assert f'<link rel="manifest" href="{reverse("frontend:manifest")}">' in anon_client.get("/").content.decode()


def test_page_is_named_after_the_tenant(tenant, other_tenant):
    """Each hostname gets its own page."""
    response = Client(HTTP_HOST="other.localhost").get("/")

    assert f"<title>{escape(other_tenant.display_name)}</title>" in response.content.decode()


def test_page_is_described_in_the_language_of_the_page(tenant):
    """Search engines get a description; it is Czech like <html lang> for every reader, so the body stays shared."""
    english = Client(HTTP_HOST="localhost", HTTP_ACCEPT_LANGUAGE="en").get("/").content.decode()
    czech = Client(HTTP_HOST="localhost").get("/").content.decode()

    assert english == czech
    assert f'<meta name="description" content="Zpěvník {escape(tenant.display_name)}:' in czech


def test_unknown_category_gets_the_page_with_404(anon_client, tenant):
    """The client says the category is missing; the status keeps it out of the service worker's cache."""
    response = anon_client.get(reverse("category:index", kwargs={"slug": "nope"}))

    assert response.status_code == 404
    assert 'id="app"' in response.content.decode()


def test_category_of_another_tenant_is_not_found(anon_client, other_category):
    """Categories are not reachable across tenants."""
    assert anon_client.get(reverse("category:index", kwargs={"slug": other_category.slug})).status_code == 404


def test_page_has_etag_and_revalidates(anon_client, tenant):
    """The page is stored by the browser but checked on every use."""
    response = anon_client.get("/")

    assert response["ETag"]
    assert response["Cache-Control"] == "no-cache"


def test_matching_etag_answers_304(anon_client, tenant):
    """An unchanged page costs no body."""
    etag = anon_client.get("/")["ETag"]

    assert anon_client.get("/", HTTP_IF_NONE_MATCH=etag).status_code == 304


def test_etag_follows_the_content(anon_client, tenant, make_category):
    """A new category changes the bootstrap and with it the page."""
    etag = anon_client.get("/")["ETag"]

    make_category(tenant, name="Fresh", slug="fresh")

    assert anon_client.get("/")["ETag"] != etag


@pytest.mark.parametrize("client_fixture", ["anon_client", "plain_client", "staff_client", "superuser_client"])
def test_page_does_not_vary_on_the_user(request, client_fixture, tenant):
    """No cookie is read or set, so any cache may keep one copy for everybody."""
    response = request.getfixturevalue(client_fixture).get("/")

    assert "Cookie" not in response.get("Vary", "")
    assert "Set-Cookie" not in response


def test_page_is_the_same_for_every_user(anon_client, superuser_client, tenant):
    """Nothing in it depends on who asks."""
    assert anon_client.get("/").content == superuser_client.get("/").content


def test_page_leaves_messages_for_the_api(staff_client, song):
    """A message queued by a view survives the redirect into the page and is still there for /api/me."""
    response = staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}), follow=True)

    assert response.status_code == 200
    assert len(json.loads(staff_client.get(reverse("chords:me")).content)["messages"]) == 1


def test_policy_allows_no_eval_and_no_foreign_origin_for_the_reader(anon_client, tenant):
    """The reader needs nothing but its own files, so the page is served with the policy the admin pages share."""
    policy = anon_client.get("/")["Content-Security-Policy"]

    assert "'unsafe-eval'" not in policy
    assert "cdnjs.cloudflare.com" not in policy
    assert "worker-src 'self'" in policy
