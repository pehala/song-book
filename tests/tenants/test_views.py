"""Tests for the tenant settings page."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

EDIT_URL = reverse("tenants:edit")


def tenant_payload(tenant, **overrides):
    """Valid UserTenantForm data"""
    data = {
        "hostname": tenant.hostname,
        "name": tenant.name,
        "display_name": tenant.display_name,
        "index_redirect": tenant.index_redirect,
        "all_songs_category": True,
        "links": [],
        # admins is a required ManyToMany on the model, so it has to be resubmitted
        "admins": list(tenant.admins.values_list("pk", flat=True)),
    }
    data.update(overrides)
    return data


def test_page_edits_the_current_tenant(staff_client, tenant):
    """The form always edits the tenant serving the request"""
    response = staff_client.get(EDIT_URL)

    assert response.context["object"] == tenant


def test_hostname_cannot_be_changed(staff_client, tenant):
    """The hostname identifies the tenant and stays read only"""
    response = staff_client.get(EDIT_URL)

    assert response.context["form"].fields["hostname"].disabled


def test_display_name_can_be_changed(staff_client, tenant):
    """Saving the form stores the new title"""
    staff_client.post(EDIT_URL, tenant_payload(tenant, display_name="Renamed"))

    tenant.refresh_from_db()
    assert tenant.display_name == "Renamed"


def test_submitted_hostname_is_ignored(staff_client, tenant):
    """A tampered hostname does not reach the database"""
    staff_client.post(EDIT_URL, tenant_payload(tenant, hostname="evil.test"))

    tenant.refresh_from_db()
    assert tenant.hostname == "localhost"


def test_invalid_submission_is_redisplayed(staff_client, tenant):
    """An empty name redisplays the form"""
    response = staff_client.post(EDIT_URL, tenant_payload(tenant, name=""))

    assert response.status_code == 200
    assert response.context["form"].errors
