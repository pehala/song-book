"""Middleware containing forwarding variables from settings to templates"""
import asyncio

from django.conf import settings
from django.utils.decorators import async_only_middleware, sync_and_async_middleware


@sync_and_async_middleware
def SiteNameMiddleware(get_response):
    """Adds SITE_NAME setting to the request"""
    if asyncio.iscoroutinefunction(get_response):
        async def middleware(request):
            request.SITE_NAME = settings.SITE_NAME
            # Do something here!
            response = await get_response(request)
            return response

    else:
        def middleware(request):
            request.SITE_NAME = settings.SITE_NAME
            # Do something here!
            response = get_response(request)
            return response

    return middleware
