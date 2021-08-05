"""Module for menu items stored in cache"""
from django.core.cache import cache
from menu import MenuItem


class CacheMenuItem(MenuItem):
    """MenuItem that has dynamic children stored in cache"""
    def __init__(self, generate_function, key, timeout, **kwargs):
        self.generate_function = generate_function
        self.key = key
        self.timeout = timeout
        super().__init__(children=self._callable, **kwargs)

    def _callable(self, _):
        """Returns children from cache or generate new one"""
        if self.key in cache:
            return cache.get(self.key)
        children = self.generate_function()
        cache.set(self.key, children, timeout=self.timeout)
        return children
