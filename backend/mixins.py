"""General mixins"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from backend.auth import is_localadmin, is_superadmin

# pylint: disable=no-member


class RegenerateViewMixin:
    """Mixin which tell you if the object changed or not"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.regenerate = None

    def form_valid(self, form):
        """Check if there were any changes"""
        if len(form.changed_data) > 0:
            self.regenerate = True
        else:
            self.regenerate = False

        return super().form_valid(form)


class PassRequestToFormMixin:
    """Passes request to a Form"""

    def get_form_kwargs(self):
        """Add request to Form kwargs"""
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs


class LocalAdminRequired(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for checking if the user can administer current Tenant"""

    def test_func(self):
        return is_localadmin(self.request)


class SuperAdminRequired(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for checking if the user can administer the entire site, including Django admin"""

    def test_func(self):
        return is_superadmin(self.request)


class RedirectToNextMixin:
    """Mixin for redirecting to the page specified in next parameter"""

    default_next_page = None

    def get_success_url(self):
        """Returns success_url to redirect to"""
        if "next" in self.request.GET:
            return self.request.GET["next"]
        if "next" in self.request.POST:
            return self.request.POST["next"]
        return self.default_next_page
