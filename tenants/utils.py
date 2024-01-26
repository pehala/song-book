"""Utility methods"""

from tenants.models import Tenant


def create_tenant_string(tenant: Tenant, key):
    """Creates string that contains tenant id"""
    return f"{tenant.id}-{key}"
