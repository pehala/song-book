"""Tests for the header the pages rendered by the server share with the reader."""

import json
import re

import pytest
from django.urls import reverse

from tenants.bootstrap import bootstrap_payload

pytestmark = pytest.mark.django_db


def inlined(response, name):
    """The JSON a page carries in `<script id=name>`."""
    return json.loads(
        re.search(rf'<script id="{name}" type="application/json">(.*?)</script>', response.content.decode()).group(1)
    )


def test_server_pages_mount_the_header(staff_client, tenant):
    """The header is drawn by the same script as in the reader."""
    html = staff_client.get(reverse("category:list")).content.decode()

    assert '<div id="site-header"></div>' in html
    assert '<script type="module" src="/static/app/site.js"></script>' in html
    assert '<link rel="stylesheet" type="text/css" href="/static/app/header.css">' in html


def test_server_pages_carry_the_bootstrap(staff_client, tenant, category):
    """Navigation comes inlined, as in the reader."""
    boot = inlined(staff_client.get(reverse("category:list")), "boot")

    assert boot == json.loads(json.dumps(bootstrap_payload(tenant)))


@pytest.mark.parametrize(
    ("client_fixture", "url", "user"),
    [
        pytest.param("staff_client", reverse("category:list"), (True, "staff", True, False), id="signed in"),
        pytest.param("anon_client", "/accounts/login/", (False, None, False, False), id="anonymous"),
    ],
)
def test_server_pages_carry_the_user(request, tenant, client_fixture, url, user):
    """Who is signed in, if anybody, comes inlined, so the header needs no request."""
    me = inlined(request.getfixturevalue(client_fixture).get(url), "me")

    assert (me["auth"], me["username"], me["localadmin"], me["superuser"]) == user


def test_server_pages_leave_messages_to_the_page(staff_client, song):
    """The page prints its messages itself, so the header's copy of the user holds none."""
    staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}))
    response = staff_client.get(reverse("category:list"))

    assert inlined(response, "me")["messages"] == []
    assert "Úspěšně smazáno" in response.content.decode()


def test_server_pages_set_the_csrf_cookie(anon_client, tenant):
    """The header's POSTs (language, logout) need the cookie on every page."""
    assert "csrftoken" in anon_client.get("/accounts/login/").cookies
