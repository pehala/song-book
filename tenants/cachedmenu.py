"""Menu entries of a tenant, generated once and stored in the cache"""

from functools import partial

from django.core.cache import cache

from tenants.utils import tenant_cache_key


class CachedMenu:
    """Generates the entries of a menu per tenant and keeps them in the cache until something clears the key"""

    def __init__(self, generate_function, cache_key, timeout):
        self.generate_function = generate_function
        self.cache_key = cache_key
        self.timeout = timeout

    def children_of(self, tenant):
        """Returns the entries of the tenant from cache or generates new ones"""
        key = tenant_cache_key(tenant, self.cache_key)
        return cache.get_or_set(key, partial(self.generate_function, tenant), timeout=self.timeout)
