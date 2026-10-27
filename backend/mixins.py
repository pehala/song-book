"""General mixins."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.http import url_has_allowed_host_and_scheme

from backend.auth import is_localadmin, is_superadmin


class RegenerateViewMixin:
    """Mixin which tell you if the object changed or not."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regenerate = None

    def form_valid(self, form):
        """Check if there were any changes."""
        if len(form.changed_data) > 0:
            self.regenerate = True
        else:
            self.regenerate = False

        return super().form_valid(form)


class PassRequestToFormMixin:
    """Passes request to a Form."""

    def get_form_kwargs(self):
        """Add request to Form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class TenantObjectsMixin:
    """Limits the objects a view can reach to those of the current Tenant."""

    def get_queryset(self):
        """Returns the objects of the current Tenant."""
        return super().get_queryset().filter(tenant=self.request.tenant)


class LocalAdminRequired(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for checking if the user can administer current Tenant."""

    def test_func(self):
        """Allows local admins."""
        return is_localadmin(self.request)


class SuperAdminRequired(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for checking if the user can administer the entire site, including Django admin."""

    def test_func(self):
        """Allows superadmins."""
        return is_superadmin(self.request)


class RedirectToNextMixin:
    """Mixin for redirecting to the page specified in next parameter."""

    default_next_page = None

    def next_url(self):
        """Returns the page named by the next parameter when it is on this site, and an empty string otherwise."""
        for source in (self.request.GET, self.request.POST):
            url = source.get("next", "")
            if url_has_allowed_host_and_scheme(
                url, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()
            ):
                return url
        return ""

    def get_success_url(self):
        """Returns success_url to redirect to."""
        return self.next_url() or self.default_next_page or self.success_url
