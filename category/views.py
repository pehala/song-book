"""Views for categories"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _
from django.views.generic.detail import SingleObjectMixin

from analytics.views import AnalyticsMixin
from backend.views import SongListView, RegenerateViewMixin
from category.forms import CategoryForm
from category.models import Category
from pdf.models.request import PDFRequest, RequestType, Status
from pdf.utils import request_pdf_regeneration


class CategorySongsListView(SongListView, AnalyticsMixin):
    """Shows all songs in a category"""

    def get_key(self):
        return self.kwargs["slug"]

    def get_queryset(self):
        slug = self.kwargs["slug"]
        if not Category.objects.filter(slug=slug).exists():
            raise Http404(_("Songbook on url /%(slug)s does not exists") % {"slug": slug})
        return super().get_queryset().filter(categories__slug=slug)


@method_decorator(login_required, name="dispatch")
class CategoryListView(ListView):
    """Lists all categories"""

    model = Category
    template_name = "category/list.html"
    context_object_name = "categories"

    def get_context_data(self, *, object_list=None, **kwargs):
        ctx = super().get_context_data(object_list=object_list, **kwargs)
        ctx["already_staged"] = PDFRequest.objects.filter(type=RequestType.EVENT, status=Status.QUEUED).values_list(
            "category_id", flat=True
        )
        return ctx


@method_decorator(login_required, name="dispatch")
class CategoryCreateView(SuccessMessageMixin, CreateView):
    """Create new category"""

    form_class = CategoryForm
    model = Category
    template_name = "category/add.html"
    success_url = reverse_lazy("category:list")
    success_message = _("Songbook %(name)s was successfully created")

    def get_success_message(self, cleaned_data):
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return super().get_success_message(cleaned_data)


@method_decorator(login_required, name="dispatch")
class CategoryUpdateView(SuccessMessageMixin, RegenerateViewMixin, UpdateView):
    """Updates category"""

    form_class = CategoryForm
    model = Category
    template_name = "category/add.html"
    success_url = reverse_lazy("category:list")
    success_message = _("Songbook %(name)s was successfully updated")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if self.regenerate:
            request_pdf_regeneration(self.object)
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return response


@method_decorator(login_required, name="dispatch")
class CategoryRegeneratePDFView(View, SingleObjectMixin):
    """Creates PDF regeneration request for Category, if it doesn't already exist"""

    model = Category

    def get(self, request, *args, **kwargs):
        """GET Request"""
        category = self.get_object()
        request_pdf_regeneration(category)
        messages.success(
            request,
            _("Category %s was successfully staged for PDF generation") % category.name,
        )
        return redirect("category:list")


@method_decorator(login_required, name="dispatch")
class CategoryDeleteView(DeleteView):
    """Removes category"""

    model = Category
    template_name = "category/confirm_delete.html"
    success_url = reverse_lazy("category:list")
    success_message = _("Songbook %(name)s was successfully deleted")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.__dict__)
        response = super().post(request, *args, **kwargs)
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return response
