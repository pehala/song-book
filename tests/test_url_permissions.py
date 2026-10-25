"""Access control matrix for every URL in the project.

Each view is classified as public, local-admin only or super-admin only, and the
same four expectations are asserted for all of them:

* anonymous visitors are redirected to the login page
* logged in users without rights get 403
* users with rights are let through (any non-error status)

The individual views' behaviour is asserted in the per-app test modules.
"""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def url(name, source=None):
    """A url under test, named after itself, optionally needing a fixture for its pk"""
    return pytest.param(name, source, id=name)


LOCAL_ADMIN_URLS = [
    url("backend:add"),
    url("backend:edit", "song"),
    url("backend:delete", "song"),
    url("category:list"),
    url("category:add"),
    url("category:edit", "category"),
    url("category:delete", "category"),
    url("category:edit_all"),
    url("pdf:files:list"),
    url("pdf:files:edit", "pdf_file"),
    url("pdf:files:delete", "pdf_file"),
    url("pdf:files:template_edit", "pdf_file"),
    url("pdf:templates:list"),
    url("pdf:templates:new"),
    url("pdf:templates:edit", "manual_template"),
    url("pdf:templates:delete", "manual_template"),
    url("pdf:templates:assign", "manual_template"),
    url("pdf:templates:generate", "manual_template"),
    url("analytics:index"),
    url("analytics:data"),
    url("tenants:edit"),
]

SUPER_ADMIN_URLS = [
    url("category:move"),
    url("pdf:templates:move"),
]

PUBLIC_URLS = [
    url("chords:index"),
    url("chords:all"),
    url("chords:songs_api"),
    url("category:index", "slug"),
    url("pdf:files:wait", "pdf_file"),
    url("pdf:files:info", "pdf_file"),
]

LOGIN_URL = "/accounts/login/"


@pytest.fixture
def url_for(request):
    """Resolves a (url name, fixture name) pair into a concrete URL"""

    def resolve(name, source):
        if source is None:
            return reverse(name)
        if source == "slug":
            return reverse(name, kwargs={"slug": request.getfixturevalue("category").slug})
        return reverse(name, kwargs={"pk": request.getfixturevalue(source).pk})

    return resolve


@pytest.mark.parametrize("name,source", LOCAL_ADMIN_URLS + SUPER_ADMIN_URLS)
def test_anonymous_is_redirected_to_login(anon_client, url_for, name, source):
    """Anonymous visitors never reach an administrative page"""
    response = anon_client.get(url_for(name, source))
    assert response.status_code == 302
    assert response["Location"].startswith(LOGIN_URL)


@pytest.mark.parametrize("name,source", LOCAL_ADMIN_URLS + SUPER_ADMIN_URLS)
def test_user_without_rights_is_forbidden(plain_client, url_for, name, source):
    """A logged in user who administers nothing gets 403"""
    assert plain_client.get(url_for(name, source)).status_code == 403


@pytest.mark.parametrize("name,source", LOCAL_ADMIN_URLS)
def test_local_admin_is_allowed(staff_client, url_for, name, source):
    """A Tenant administrator can open every tenant-level page"""
    assert staff_client.get(url_for(name, source)).status_code < 400


@pytest.mark.parametrize("name,source", SUPER_ADMIN_URLS)
def test_local_admin_cannot_reach_superadmin_pages(staff_client, url_for, name, source):
    """Tenant administrators are not site administrators"""
    assert staff_client.get(url_for(name, source)).status_code == 403


@pytest.mark.parametrize("name,source", SUPER_ADMIN_URLS)
def test_superuser_is_allowed(superuser_client, url_for, name, source):
    """Site administrators can open the cross-tenant pages"""
    assert superuser_client.get(url_for(name, source)).status_code < 400


@pytest.mark.parametrize("name,source", PUBLIC_URLS)
def test_public_urls_need_no_login(anon_client, url_for, name, source):
    """Public pages are reachable without logging in"""
    assert anon_client.get(url_for(name, source)).status_code < 400
