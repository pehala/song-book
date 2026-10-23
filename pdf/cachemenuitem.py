"""Module for menu items stored in cache"""

from functools import partial

from django.core.cache import cache
from simple_menu import MenuItem

from tenants.utils import tenant_cache_key


class CacheMenuItem(MenuItem):
    """MenuItem whose children are generated per tenant and stored in cache"""

    def __init__(self, generate_function, cache_key, timeout, **kwargs):
        self.generate_function = generate_function
        self.cache_key = cache_key
        self.timeout = timeout
        super().__init__(children=self.children_for, **kwargs)

    def children_for(self, request):
        """Returns children of the request's tenant from cache or generates new ones"""
        key = tenant_cache_key(request.tenant, self.cache_key)
        return cache.get_or_set(key, partial(self.generate_function, request.tenant), timeout=self.timeout)


class HideWhenEmptyCacheMenuItem(CacheMenuItem):
    """CacheMenuItem that is hidden when the tenant has no children"""

    def check(self, request):
        """Visible only when there is at least one child"""
        self.visible = bool(self.children_for(request))
