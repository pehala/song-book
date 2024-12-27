"""Views for categories"""

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.translation import gettext_lazy as _, get_language, gettext
from django.views.generic import ListView

from analytics.views import AnalyticsMixin
from backend.generic import UniversalDeleteView, UniversalUpdateView, UniversalCreateView
from backend.mixins import RegenerateViewMixin, LocalAdminRequired
from backend.models import Song
from backend.views import BaseSongListView
from category.forms import CategoryForm, NameForm
from category.models import Category
from category.utils import request_pdf_regeneration
from pdf.models.request import PDFTemplate, PDFFile
from tenants.views import AdminMoveView


class CategorySongsListView(BaseSongListView, AnalyticsMixin):
    """Shows all songs in a category"""

    def get_key(self):
        return self.kwargs["slug"]

    def category_queryset(self):
        """Returns queryset for this category"""
        return Category.objects.filter(slug=self.kwargs["slug"], tenant=self.request.tenant)

    def get_queryset(self):
        slug = self.kwargs["slug"]
        if not self.category_queryset().exists():
            raise Http404(_("Category with url /%(slug)s does not exist") % {"slug": slug})
        return super().get_queryset().filter(categories__slug=slug)

    def get_title(self):
        """Return title of this song set"""
        return f"{self.category_queryset().get().name} | {self.request.tenant.display_name}"


class CategoryListView(LocalAdminRequired, ListView):
    """Lists all categories"""

    model = Category
    template_name = "category/list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(tenant=self.request.tenant)
            .annotate(song_count=Count("song", filter=Q(song__archived=False)))
            .annotate(file_count=Count("pdffile"))
        )


class CategoryCreateView(LocalAdminRequired, UniversalCreateView):
    """Create new category"""

    form_class = CategoryForm
    model = Category
    success_url = reverse_lazy("category:list")

    def get_initial(self):
        with translation.override(get_language()):
            return {
                "tenant": self.request.tenant,
                "filename": gettext("songbook"),
                "locale": self.request.LANGUAGE_CODE,
            }

    def get_success_message(self, cleaned_data):
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return super().get_success_message(cleaned_data)


class CategoryUpdateView(LocalAdminRequired, RegenerateViewMixin, UniversalUpdateView):
    """Updates category"""

    form_class = CategoryForm
    model = Category
    success_url = reverse_lazy("category:list")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if self.regenerate and self.object.generate_pdf:
            request_pdf_regeneration(self.object)
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return response


class CategoryDeleteView(LocalAdminRequired, UniversalDeleteView):
    """Removes category"""

    model = Category
    success_url = reverse_lazy("category:list")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return response


class CategoryMoveView(AdminMoveView):
    """Moves Categories to a different Tenant"""

    formset_form = NameForm
    model = Category

    def action(self, target, ids):
        """What should happen on POST with data from forms"""
        categories = Category.objects.filter(id__in=ids)
        songs = Song.objects.filter(categories__id__in=ids).distinct()
        requests = PDFTemplate.objects.filter(category_id__in=ids).distinct()
        with transaction.atomic():
            for category in categories:
                category.tenant = target
            for request in requests:
                request.tenant = target
                for file in request.files:
                    file.tenant = target
                PDFFile.objects.bulk_update(request.files, ["tenant"])
            Category.objects.bulk_update(categories, ["tenant"])
            PDFTemplate.objects.bulk_update(requests, ["tenant"])
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
