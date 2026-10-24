"""Invalidation of the songs payload kept in the cache"""

from django.conf import settings
from django.core.cache import cache

from tenants.utils import tenant_cache_key


def songs_payload_key(tenant, include_archived):
    """Cache key of the combined songs payload of a tenant"""
    key = tenant_cache_key(tenant, settings.SONGS_CACHE_KEY)
    return f"{key}_archived" if include_archived else key


def invalidate_tenant_songs_cache(tenant):
    """Invalidates the combined songs payload of a tenant, in both its public and its archived variant"""
    cache.delete_many([songs_payload_key(tenant, include_archived) for include_archived in (False, True)])


def song_tenants(song):
    """Tenants whose song lists contain the song"""
    return {category.tenant for category in song.categories.select_related("tenant")}


def invalidate_songs_cache(song):
    """Invalidates the songs payload of every tenant the song belongs to"""
    for tenant in song_tenants(song):
        invalidate_tenant_songs_cache(tenant)
