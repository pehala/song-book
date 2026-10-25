"""Tests for the /api/me endpoint."""

import json

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

URL = reverse("chords:me")


def fetch(client):
    """Returns the decoded `/api/me` answer for the client."""
    return json.loads(client.get(URL).content)


def test_anonymous_visitor(anon_client, tenant):
    """Nobody is signed in and nothing is allowed."""
    assert fetch(anon_client) == {
        "auth": False,
        "username": None,
        "localadmin": False,
        "superuser": False,
        "messages": [],
    }


@pytest.mark.parametrize(
    ("client_fixture", "username", "localadmin", "is_superuser"),
    [
        pytest.param("plain_client", "plain", False, False, id="user without rights"),
        pytest.param("staff_client", "staff", True, False, id="tenant admin"),
        pytest.param("superuser_client", "super", True, True, id="superuser"),
    ],
)
def test_signed_in_user(request, client_fixture, username, localadmin, is_superuser):
    """A tenant administrator is a local admin only, a superuser administers every tenant."""
    data = fetch(request.getfixturevalue(client_fixture))

    assert (data["auth"], data["username"], data["localadmin"], data["superuser"]) == (
        True,
        username,
        localadmin,
        is_superuser,
    )


def test_never_stored(anon_client, tenant):
    """The answer depends on the session, so no cache may keep it."""
    assert anon_client.get(URL)["Cache-Control"] == "private, no-store"


def test_csrf_cookie_is_set_for_signed_in_users(staff_client):
    """Forms posted by the reader need the cookie to exist."""
    assert "csrftoken" in staff_client.get(URL).cookies


def test_pending_messages_are_handed_over_once(staff_client, song):
    """A message queued by a view survives the redirect into the reader and is shown a single time."""
    staff_client.post(reverse("backend:delete", kwargs={"pk": song.pk}))

    first = fetch(staff_client)["messages"]

    assert [message["level"] for message in first] == ["success"]
    assert "Test Song" in first[0]["text"]
    assert fetch(staff_client)["messages"] == []
