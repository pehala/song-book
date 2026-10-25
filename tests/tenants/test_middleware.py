"""Tests for the tenant recognition middleware."""

import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db

ALL_URL = reverse("chords:all")


@pytest.fixture
def other_client(other_tenant):
    """Client talking to the second Tenant."""
    return Client(HTTP_HOST=other_tenant.hostname)


@pytest.mark.parametrize(
    ("client_fixture", "tenant_fixture"),
    [("anon_client", "tenant"), ("other_client", "other_tenant")],
)
def test_hostname_selects_its_tenant(request, song, client_fixture, tenant_fixture):
    """The tenant is picked from the Host header, and each hostname is served by its own."""
    response = request.getfixturevalue(client_fixture).get(ALL_URL)

    assert response.wsgi_request.tenant == request.getfixturevalue(tenant_fixture)


def test_unknown_hostname_is_rejected(tenant):
    """A hostname without a tenant is a 404."""
    assert Client(HTTP_HOST="testserver").get(ALL_URL).status_code == 404


def test_unknown_hostname_falls_back_to_first_tenant_in_debug(settings, tenant, song):
    """While developing, any hostname is served by the first tenant."""
    settings.DEBUG = True

    response = Client(HTTP_HOST="testserver").get(ALL_URL)

    assert response.status_code == 200
    assert response.wsgi_request.tenant == tenant


@pytest.mark.parametrize(
    ("client_fixture", "localadmin"),
    [
        pytest.param("staff_client", True, id="tenant admin"),
        pytest.param("superuser_client", True, id="superuser"),
        pytest.param("plain_client", False, id="user without rights"),
    ],
)
def test_admins_of_the_tenant_are_marked_as_local_admins(request, song, client_fixture, localadmin):
    """Users listed as admins of the tenant and superusers get the flag, other users do not."""
    response = request.getfixturevalue(client_fixture).get(ALL_URL)

    assert response.wsgi_request.user.is_localadmin is localadmin


def test_admin_of_another_tenant_is_not_a_local_admin(staff_user, other_client, other_tenant, song):
    """Rights are not carried over to another tenant."""
    client = other_client
    client.force_login(staff_user)

    response = client.get(ALL_URL)

    assert not response.wsgi_request.user.is_localadmin
