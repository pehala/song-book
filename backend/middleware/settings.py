"""Middleware containing forwarding variables from settings to templates."""

from django.conf import settings


class SiteNameMiddleware:
    """Adds SITE_NAME setting to the request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Stores the site name in the request."""
        request.SITE_NAME = settings.SITE_NAME

        return self.get_response(request)


class CacheTimeoutMiddleware:
    """Adds CACHE_TIMEOUT setting to the request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Stores the cache timeout in the request."""
        request.CACHE_TIMEOUT = settings.CACHE_TIMEOUT

        return self.get_response(request)
