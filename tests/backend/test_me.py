"""Tests for the /api/me endpoint."""

import json

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

URL = reverse("chords:me")


def fetch(client):
    return json.loads(client.get(URL).content)


def test_anonymous_visitor(anon_client, tenant):
    """Nobody is signed in and nothing is allowed"""
    assert fetch(anon_client) == {
        "auth": False,
        "username": None,
        "localadmin": False,
        "superuser": False,
        "messages": [],
    }


def test_plain_user(plain_client):
    """A signed in user without rights"""
    data = fetch(plain_client)

    assert (data["auth"], data["username"], data["localadmin"], data["superuser"]) == (True, "plain", False, False)


def test_tenant_admin(staff_client):
    """A tenant administrator is a local admin only"""
    data = fetch(staff_client)

    assert (data["localadmin"], data["superuser"]) == (True, False)


def test_superuser(superuser_client):
    """A superuser administers every tenant"""
    data = fetch(superuser_client)

    assert (data["localadmin"], data["superuser"]) == (True, True)


def test_never_stored(anon_client, tenant):
    """The answer depends on the session, so no cache may keep it"""
    assert anon_client.get(URL)["Cache-Control"] == "private, no-store"


def test_csrf_cookie_is_set_for_signed_in_users(staff_client):
    """Forms posted by the reader need the cookie to exist"""
    assert "csrftoken" in staff_client.get(URL).cookies


def test_pending_messages_are_handed_over_once(staff_client, song):
    """A message queued by a view survives the redirect into the reader and is shown a single time"""
    staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}))

    first = fetch(staff_client)["messages"]

    assert [message["level"] for message in first] == ["success"]
    assert "Test Song" in first[0]["text"]
    assert fetch(staff_client)["messages"] == []
