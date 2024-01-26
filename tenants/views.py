"""Tenant views"""

from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView
from django.utils.translation import gettext_lazy as _

from backend.mixins import LocalAdminRequired
from tenants.forms import UserTenantForm
from tenants.models import Tenant


class TenantUpdateForm(LocalAdminRequired, UpdateView, SuccessMessageMixin):
    """Tenant update view"""

    form_class = UserTenantForm
    model = Tenant
    template_name = "tenant/add.html"
    success_url = reverse_lazy("backend:index")
    success_message = _("Tenant was successfully updated")

    def get_object(self, queryset=None):
        return self.request.tenant
