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


def test_known_hostname_selects_the_tenant(anon_client, tenant, song):
    """The tenant is picked from the Host header."""
    response = anon_client.get(ALL_URL)

    assert response.wsgi_request.tenant == tenant


def test_each_hostname_gets_its_own_tenant(other_client, other_tenant):
    """A second hostname is served by its own tenant."""
    response = other_client.get(ALL_URL)

    assert response.wsgi_request.tenant == other_tenant


def test_unknown_hostname_is_rejected(tenant):
    """A hostname without a tenant is a 404."""
    assert Client(HTTP_HOST="testserver").get(ALL_URL).status_code == 404


def test_unknown_hostname_falls_back_to_first_tenant_in_debug(settings, tenant, song):
    """While developing, any hostname is served by the first tenant."""
    settings.DEBUG = True

    response = Client(HTTP_HOST="testserver").get(ALL_URL)

    assert response.status_code == 200
    assert response.wsgi_request.tenant == tenant


def test_tenant_admin_is_marked_as_local_admin(staff_client, song):
    """Users listed as admins of the tenant get the flag."""
    response = staff_client.get(ALL_URL)

    assert response.wsgi_request.user.is_localadmin


def test_superuser_is_marked_as_local_admin(superuser_client, song):
    """Superusers administer every tenant."""
    response = superuser_client.get(ALL_URL)

    assert response.wsgi_request.user.is_localadmin


def test_plain_user_is_not_a_local_admin(plain_client, song):
    """Users not listed as admins do not get the flag."""
    response = plain_client.get(ALL_URL)

    assert not response.wsgi_request.user.is_localadmin


def test_admin_of_another_tenant_is_not_a_local_admin(staff_user, other_client, other_tenant, song):
    """Rights are not carried over to another tenant."""
    client = other_client
    client.force_login(staff_user)

    response = client.get(ALL_URL)

    assert not response.wsgi_request.user.is_localadmin
