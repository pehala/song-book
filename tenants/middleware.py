"""Middleware for Tenants."""

from functools import partial
from urllib.parse import urlparse

from django.conf import settings
from django.http import Http404
from django.utils.functional import SimpleLazyObject

from tenants.models import Tenant


def with_localadmin(request, user):
    """Marks whether the user administers the request's tenant; reading the user is deferred until it is needed."""
    user.is_localadmin = (
        user.is_authenticated and request.tenant.admins.filter(id=user.id).exists() or user.is_superuser
    )
    return user


class RecognizeTenantMiddleware:
    """Fills in current Tenant being used."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Resolves the tenant by hostname and sets it, with the lazy local admin flag, on the request."""
        try:
            # if "admin" not in path:
            hostname = urlparse(request.build_absolute_uri()).hostname
            query_set = Tenant.objects.filter(hostname=hostname)
            if not query_set.exists():
                raise Http404(f"Unable to find Tenant for hostname {hostname}")
            request.tenant = query_set.first()
            request.user = SimpleLazyObject(partial(with_localadmin, request, request.user))
        except Http404:
            if settings.DEBUG:
                request.tenant = Tenant.objects.first()
            else:
                raise
        response = self.get_response(request)
        return response
