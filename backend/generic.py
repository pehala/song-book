"""Generic CRUD views"""

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, UpdateView, CreateView

from backend.mixins import RedirectToNextMixin

# pylint: disable=no-member


class UniversalView(RedirectToNextMixin):
    """Mixing for rest of the classes, simplifies object identifier and verbose name retrieval"""

    def get_verbose_name(self):
        """Returns model verbose name"""
        return self.model._meta.verbose_name

    def get_object_identifier(self, obj):
        """Returns Object identifier"""
        if hasattr(obj, "name"):
            return obj.name
        return obj.id


class UniversalDeleteView(UniversalView, DeleteView):
    """
    Universal Delete view for all Models
    You need to add 'success_url' and 'model' class parameters
    """

    template_name = "base/verbs/delete.html"
    success_message = _("%(class)s %(identifier)s was successfully deleted")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = ctx["object"]
        ctx["success_url"] = self.success_url
        ctx["model_verbose_name"] = self.get_verbose_name()
        ctx["identifier"] = self.get_object_identifier(obj)
        return ctx

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        response = super().post(request, *args, **kwargs)
        messages.success(
            self.request,
            self.success_message % {"class": self.get_verbose_name(), "identifier": self.get_object_identifier(obj)},
        )
        return response


class UniversalEditView(
    UniversalView,
    SuccessMessageMixin,
):
    """UniversalEditView base class"""

    template_name = "base/verbs/add.html"
    success_message = _("%(class)s %(identifier)s was successfully updated")

    def get_success_message(self, cleaned_data):
        return self.success_message % {
            "class": self.get_verbose_name(),
            "identifier": self.get_object_identifier(self.object),
        }


class UniversalUpdateView(UniversalEditView, UpdateView):
    """
    Universal Update view for all Models
    You need to add 'success_url', 'form_class' and 'model' class parameters
    """

    success_message = _("%(class)s %(identifier)s was successfully updated")
    title_message = _("Update %(class)s %(identifier)s")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.title_message % {
            "class": self.get_verbose_name(),
            "identifier": self.get_object_identifier(self.object),
        }
        return ctx


class UniversalCreateView(UniversalEditView, CreateView):
    """
    Universal Update view for all Models
    You need to add 'success_url', 'form_class' and 'model' class parameters
    """

    success_message = _("%(class)s %(identifier)s was successfully created")
    title_message = _("Create %(class)s")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = self.title_message % {"class": self.get_verbose_name()}
        return ctx
