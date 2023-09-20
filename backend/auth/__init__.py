"""Helper methods for AuthZ"""


def is_superadmin(request):
    """Returns True, if the current user is super admin"""
    return request.user.is_authenticated and request.user.is_superuser


def is_localadmin(request):
    """Returns True, if the current user is Tenant-level administrator"""
    user = request.user
    return user.is_authenticated and request.tenant.admins.filter(id=user.id).exists() or is_superadmin(request)


def is_authenticated(request):
    """Returns True, if the current user is logged in"""
    return request.user.is_authenticated


def is_not_authenticated(request):
    """Returns True, if the current user is NOT logged in"""
    return not request.user.is_authenticated
