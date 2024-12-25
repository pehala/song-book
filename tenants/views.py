"""Tenant views"""

import abc

from django.forms import formset_factory
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from backend.generic import UniversalUpdateView
from backend.mixins import LocalAdminRequired, SuperAdminRequired
from tenants.forms import UserTenantForm, ChooseTenantForm
from tenants.models import Tenant


class TenantUpdateForm(LocalAdminRequired, UniversalUpdateView):
    """Tenant update view"""

    form_class = UserTenantForm
    model = Tenant
    success_url = reverse_lazy("backend:index")

    def get_object(self, queryset=None):
        return self.request.tenant


class AdminMoveView(SuperAdminRequired, TemplateView):
    """Moves Categories to a different Tenant"""

    template_name = "admin/base/migrate.html"
    form_class = ChooseTenantForm
    formset_form = None
    model = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formset_class = formset_factory(self.formset_form, extra=0)

    def initial(self, pks):
        """Initial Form population"""
        query = self.model.objects.filter(id__in=pks)

        initial = []
        for instance in query:
            initial.append({"pk": instance.pk, "name": instance.name})

        return initial

    def get_context_data(self, **kwargs):
        """Appends Form and Formset"""
        context = super().get_context_data(**kwargs)

        initial = {}
        if "pk" in self.request.GET:
            initial = self.initial(self.request.GET.getlist("pk"))

        context["form"] = self.form_class()
        context["formset"] = self.formset_class(initial=initial)
        context["source_verbose_name_plural"] = self.model._meta.verbose_name_plural
        context["target_verbose_name"] = Tenant._meta.verbose_name
        return context

    def post(self, request, *args, **kwargs):
        """POST request"""
        form = self.form_class(request.POST)
        formset = self.formset_class(request.POST)
        if form.is_valid() and formset.is_valid():
            tenant = form.cleaned_data["tenant"]
            ids = [inline_form.cleaned_data["pk"] for inline_form in formset]
            self.action(tenant, ids)
            return redirect("admin:index")
        return self.render_to_response(self.get_context_data(**kwargs))

    @abc.abstractmethod
    def action(self, target, ids):
        """What should happen on the move"""
