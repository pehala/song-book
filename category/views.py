"""Views for categories"""
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.db import transaction
from django.forms import formset_factory
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from analytics.views import AnalyticsMixin
from backend.models import Song
from backend.views import BaseSongListView
from backend.mixins import RegenerateViewMixin, LocalAdminRequired, SuperAdminRequired
from category.forms import CategoryForm, NameForm, ChooseTenantForm
from category.models import Category
from pdf.models.request import PDFRequest, RequestType, Status
from pdf.utils import request_pdf_regeneration


class CategorySongsListView(BaseSongListView, AnalyticsMixin):
    """Shows all songs in a category"""

    def get_key(self):
        return self.kwargs["slug"]

    def get_queryset(self):
        slug = self.kwargs["slug"]
        if not Category.objects.filter(slug=slug, tenant=self.request.tenant).exists():
            raise Http404(_("Category with url /%(slug)s does not exist") % {"slug": slug})
        return super().get_queryset().filter(categories__slug=slug)


class CategoryListView(LocalAdminRequired, ListView):
    """Lists all categories"""

    model = Category
    template_name = "category/list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return super().get_queryset().filter(tenant=self.request.tenant)

    def get_context_data(self, *, object_list=None, **kwargs):
        ctx = super().get_context_data(object_list=object_list, **kwargs)
        ctx["already_staged"] = PDFRequest.objects.filter(
            type=RequestType.EVENT, status__in=[Status.QUEUED, Status.SCHEDULED], tenant=self.request.tenant
        ).values_list("category_id", flat=True)
        return ctx


class CategoryCreateView(LocalAdminRequired, SuccessMessageMixin, CreateView):
    """Create new category"""

    form_class = CategoryForm
    model = Category
    template_name = "category/add.html"
    success_url = reverse_lazy("category:list")
    success_message = _("Category %(name)s was successfully created")

    def get_success_message(self, cleaned_data):
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return super().get_success_message(cleaned_data)


class CategoryUpdateView(LocalAdminRequired, SuccessMessageMixin, RegenerateViewMixin, UpdateView):
    """Updates category"""

    form_class = CategoryForm
    model = Category
    template_name = "category/add.html"
    success_url = reverse_lazy("category:list")
    success_message = _("Category %(name)s was successfully updated")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if self.regenerate:
            request_pdf_regeneration(self.object)
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return response


class CategoryRegeneratePDFView(LocalAdminRequired, View, SingleObjectMixin):
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


class CategoryDeleteView(LocalAdminRequired, DeleteView):
    """Removes category"""

    model = Category
    template_name = "category/confirm_delete.html"
    success_url = reverse_lazy("category:list")
    success_message = _("Category %(name)s was successfully deleted")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.__dict__)
        response = super().post(request, *args, **kwargs)
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return response


class CategoryMoveView(SuperAdminRequired, TemplateView):
    """Moves Categories to a different Tenant"""

    template_name = "admin/category/migrate.html"
    form_class = ChooseTenantForm
    formset_class = formset_factory(NameForm, extra=0)

    def initial(self, pks):
        """Initial Form population"""
        query = Category.objects.filter(id__in=pks)

        form = self.form_class()
        initial = []
        for category in query.values_list("id", "name"):
            initial.append({"pk": category[0], "name": category[1]})

        formset = self.formset_class(initial=initial)
        return form, formset

    def get_context_data(self, **kwargs):
        """Appends Form and Formset"""
        context = super().get_context_data(**kwargs)

        pks = self.request.GET.getlist("pk")
        form, formset = self.initial(pks)

        context["form"] = form
        context["formset"] = formset
        return context

    def action(self, tenant, ids):
        """What should happen on POST with data from forms"""
        categories = Category.objects.filter(id__in=ids)
        songs = Song.objects.filter(categories__id__in=ids).distinct()
        requests = PDFRequest.objects.filter(category_id__in=ids).distinct()
        with transaction.atomic():
            for category in categories:
                category.tenant = tenant
            for request in requests:
                request.tenant = tenant
            Category.objects.bulk_update(categories, ["tenant"])
            PDFRequest.objects.bulk_update(requests, ["tenant"])
            for song in songs:
                to_keep = []
                to_remove = []
                for song_category in song.categories.all():
                    if song_category.id in ids:
                        to_keep.append(song_category)
                    else:
                        to_remove.append(song_category)
                if len(to_remove) != 0:
                    song.categories.set(to_keep)
                    song.save()
                    song.id = None
                    song.save()
                    song.categories.set(to_remove)
                    song.save()

    def post(self, request, *args, **kwargs):
        """POST request"""
        form = self.form_class(request.POST)
        formset = self.formset_class(request.POST)
        if all([form.is_valid(), formset.is_valid()]):
            tenant = form.cleaned_data["tenant"]
            ids = [inline_form.cleaned_data["pk"] for inline_form in formset]
            self.action(tenant, ids)
            return redirect("admin:index")
        return self.render_to_response({"form": form, "formset": formset})
