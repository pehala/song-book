"""Tests for the AuthZ helper predicates.

These predicates decide who gets past `LocalAdminRequired` / `SuperAdminRequired`
and what `/api/me` reports, so what matters is the whole truth table: which visitor
passes which check.
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from backend.auth import is_localadmin, is_superadmin

pytestmark = pytest.mark.django_db

ANONYMOUS = "anonymous"
PLAIN = "plain user"
TENANT_ADMIN = "tenant admin"
SUPERUSER = "superuser"

USER_FIXTURES = {PLAIN: "plain_user", TENANT_ADMIN: "staff_user", SUPERUSER: "superuser"}


@pytest.fixture
def visitor_request(request):
    """Builds a request for the named visitor, with the flags the tenant middleware sets."""

    def build(visitor):
        user = AnonymousUser() if visitor == ANONYMOUS else request.getfixturevalue(USER_FIXTURES[visitor])
        http_request = RequestFactory().get("/")
        http_request.user = user
        # RecognizeTenantMiddleware sets this on every request
        user.is_localadmin = visitor == TENANT_ADMIN or user.is_superuser
        return http_request

    return build


@pytest.mark.parametrize(
    ("visitor", "superadmin", "localadmin"),
    [
        pytest.param(ANONYMOUS, False, False, id=ANONYMOUS),
        pytest.param(PLAIN, False, False, id=PLAIN),
        pytest.param(TENANT_ADMIN, False, True, id=TENANT_ADMIN),
        pytest.param(SUPERUSER, True, True, id=SUPERUSER),
    ],
)
def test_who_passes_each_check(visitor_request, visitor, superadmin, localadmin):
    """A tenant admin administers only their own tenant; only a superuser administers the site."""
    http_request = visitor_request(visitor)

    assert is_superadmin(http_request) is superadmin
    assert is_localadmin(http_request) is localadmin
