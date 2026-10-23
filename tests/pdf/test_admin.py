"""Tests for the PDF template admin."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.urls import reverse

from pdf.admin import RequestAdmin
from pdf.models.request import ManualPDFTemplate

pytestmark = pytest.mark.django_db


@pytest.fixture
def template_admin():
    return RequestAdmin(ManualPDFTemplate, AdminSite())


def test_tenant_column_links_to_the_tenant(template_admin, manual_template, tenant):
    """The changelist links each template to its owning tenant"""
    rendered = template_admin.tenant_name(manual_template)

    assert reverse("admin:tenants_tenant_change", args=[tenant.id]) in rendered
    assert tenant.name in rendered


def test_move_action_redirects_to_the_move_page(template_admin, manual_template, rf):
    """The bulk action hands the selection over to the move view"""
    queryset = ManualPDFTemplate.objects.filter(pk=manual_template.pk)

    response = template_admin.move_tenant(rf.get("/"), queryset)

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("pdf:templates:move"))
    assert f"pk={manual_template.pk}" in response["Location"]


def test_changelist_renders(superuser_client, manual_template):
    """The template changelist is reachable for site administrators"""
    assert superuser_client.get("/admin/pdf/manualpdftemplate/").status_code == 200
