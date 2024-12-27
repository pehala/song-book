"""Module for menu items stored in cache"""

from functools import partial

from django.core.cache import cache
from menu import MenuItem


class CacheMenuItem(MenuItem):
    """MenuItem that has dynamic children stored in cache"""

    def __init__(self, generate_function, key, timeout, **kwargs):
        self.generate_function = generate_function
        self.key = key
        self.timeout = timeout
        super().__init__(children=self._callable, **kwargs)

    def _callable(self, request):
        """Returns children from cache or generate new one"""
        return cache.get_or_set(self.key, partial(self.generate_function, request), timeout=self.timeout)
