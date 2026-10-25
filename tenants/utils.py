"""Utility methods."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tenants.models import Tenant


def tenant_cache_key(tenant: Tenant, key):
    """Creates string that contains tenant id."""
    return f"{tenant.id}-{key}"
