"""Utility methods"""

from tenants.models import Tenant


def tenant_cache_key(tenant: Tenant, key):
    """Creates string that contains tenant id"""
    return f"{tenant.id}-{key}"
