"""Invalidation of the songs JSON lists kept in the cache"""

from django.conf import settings
from django.core.cache import cache

from tenants.utils import tenant_cache_key


def invalidate_tenant_songs_cache(tenant, extra_slugs=()):
    """
    Invalidates every songs JSON cache entry of a tenant: the "all" list and each category list.

    extra_slugs lets callers clear lists of slugs that no longer exist (renamed or deleted categories).
    """
    slugs = [*tenant.category_set.values_list("slug", flat=True), *extra_slugs]
    for name in ["ALL", *slugs]:
        key = tenant_cache_key(tenant, f"{settings.SONGS_CACHE_KEY}_{name}")
        cache.delete(key)
        cache.delete(f"{key}_archived")


def song_tenants(song):
    """Tenants whose song lists contain the song"""
    return {category.tenant for category in song.categories.select_related("tenant")}


def invalidate_songs_cache(song):
    """Invalidates songs JSON cache for every tenant the song belongs to"""
    for tenant in song_tenants(song):
        invalidate_tenant_songs_cache(tenant)
