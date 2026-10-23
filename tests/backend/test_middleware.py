"""Tests for the backend middlewares."""

from django.http import HttpResponse
from django.test import RequestFactory

from backend.middleware.cache import DisableClientSideCachingMiddleware
from backend.middleware.settings import CacheTimeoutMiddleware, SiteNameMiddleware


def call(middleware_class, request):
    """Runs a middleware over a trivial view"""
    captured = {}

    def get_response(processed):
        captured["request"] = processed
        return HttpResponse("ok")

    response = middleware_class(get_response)(request)
    return captured["request"], response


def test_site_name_is_attached_to_request(settings):
    """Templates can read the configured site name off the request"""
    settings.SITE_NAME = "Testbook"

    request, _ = call(SiteNameMiddleware, RequestFactory().get("/"))

    assert request.SITE_NAME == "Testbook"


def test_cache_timeout_is_attached_to_request(settings):
    """Templates can read the configured cache timeout off the request"""
    settings.CACHE_TIMEOUT = 1234

    request, _ = call(CacheTimeoutMiddleware, RequestFactory().get("/"))

    assert request.CACHE_TIMEOUT == 1234


def test_client_side_caching_is_disabled():
    """Responses are marked as never cacheable by the browser"""
    _, response = call(DisableClientSideCachingMiddleware, RequestFactory().get("/"))

    assert "no-cache" in response["Cache-Control"]
    assert "max-age=0" in response["Cache-Control"]
