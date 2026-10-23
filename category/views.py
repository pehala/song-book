"""Views for categories"""

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import translation
from django.utils.translation import get_language, gettext
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from analytics.views import AnalyticsMixin
from backend.cache import invalidate_tenant_songs_cache
from backend.generic import UniversalCreateView, UniversalDeleteView, UniversalUpdateView
from backend.mixins import LocalAdminRequired, PassRequestToFormMixin, RegenerateViewMixin
from backend.models import Song
from backend.views import BaseSongListView, BaseSongsJsonView
from category.forms import CategoryForm, NameForm
from category.models import Category
from category.utils import request_pdf_regeneration
from pdf.models.request import PDFFile
from tenants.utils import tenant_cache_key
from tenants.views import AdminMoveView


class CategorySongsListView(AnalyticsMixin, BaseSongListView):
    """Shows all songs in a category"""

    def get_key(self):
        return self.kwargs["slug"]

    def get(self, request, *args, **kwargs):
        self.category = get_object_or_404(Category, slug=self.kwargs["slug"], tenant=request.tenant)
        return super().get(request, *args, **kwargs)

    def get_title(self):
        """Return title of this song set"""
        return f"{self.category.name} | {self.request.tenant.display_name}"

    def get_data_url(self):
        return reverse("category:songs_data", kwargs={"slug": self.kwargs["slug"]})


class CategorySongsJsonView(BaseSongsJsonView):
    """Returns songs JSON for a category, served from Redis cache with ETag support"""

    def get(self, request, *args, **kwargs):
        if not Category.objects.filter(slug=self.kwargs["slug"], tenant=request.tenant).exists():
            raise Http404(_("Category with url /%(slug)s does not exist") % {"slug": self.kwargs["slug"]})
        return super().get(request, *args, **kwargs)

    def get_cache_key(self):
        base = tenant_cache_key(
            self.request.tenant,
            f"{settings.SONGS_CACHE_KEY}_{self.kwargs['slug']}",
        )
        return f"{base}_archived" if self.request.user.is_superuser else base

    def get_queryset(self):
        return Song.objects.filter(categories__slug=self.kwargs["slug"], categories__tenant=self.request.tenant)


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


class CategoryCreateView(LocalAdminRequired, PassRequestToFormMixin, UniversalCreateView):
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


class CategoryUpdateView(LocalAdminRequired, PassRequestToFormMixin, RegenerateViewMixin, UniversalUpdateView):
    """Updates category"""

    form_class = CategoryForm
    model = Category
    success_url = reverse_lazy("category:list")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if self.regenerate and self.object.generate_pdf:
            request_pdf_regeneration(self.object)
        return response


class CategoryDeleteView(LocalAdminRequired, UniversalDeleteView):
    """Removes category"""

    model = Category
    success_url = reverse_lazy("category:list")


class CategoryMoveView(AdminMoveView):
    """Moves Categories to a different Tenant"""

    formset_form = NameForm
    model = Category

    def action(self, target, ids):
        """What should happen on POST with data from forms"""
        categories = Category.objects.filter(id__in=ids)
        songs = Song.objects.filter(categories__id__in=ids).distinct()
        # Categories are PDFTemplates themselves, so only their files have to follow them
        files = PDFFile.objects.filter(template_id__in=ids)
        # bulk_update sends no signals, so the lists of the source tenants are cleared by hand
        source_tenants = {category.tenant for category in categories.select_related("tenant")}
        with transaction.atomic():
            for category in categories:
                category.tenant = target
            for file in files:
                file.tenant = target
            Category.objects.bulk_update(categories, ["tenant"])
            PDFFile.objects.bulk_update(files, ["tenant"])
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
        for tenant in source_tenants | {target}:
            invalidate_tenant_songs_cache(tenant)
            cache.delete(tenant_cache_key(tenant, settings.CATEGORY_CACHE_KEY))
