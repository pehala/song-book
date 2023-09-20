"""Middleware for Tenants"""
from urllib.parse import urlparse
from django.conf import settings
from django.http import Http404

from tenants.models import Tenant


class RecognizeTenantMiddleware:
    """Fills in current Tenant being used"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # if "admin" not in path:
            hostname = urlparse(request.build_absolute_uri()).hostname
            query_set = Tenant.objects.filter(hostname=hostname)
            if not query_set.exists():
                raise Http404(f"Unable to find Tenant for hostname {hostname}")
            request.tenant = query_set.first()
        except Http404 as exception:
            if settings.DEBUG:
                request.tenant = Tenant.objects.first()
            else:
                raise exception
        response = self.get_response(request)
        return response
