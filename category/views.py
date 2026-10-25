"""Views for categories."""

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.translation import get_language, gettext
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from backend.cache import invalidate_tenant_songs_cache, touch_songs
from backend.generic import UniversalCreateView, UniversalDeleteView, UniversalUpdateView
from backend.mixins import LocalAdminRequired, PassRequestToFormMixin, RegenerateViewMixin
from backend.models import Song
from category.forms import AllSongsForm, CategoryForm, NameForm
from category.models import Category
from category.utils import request_all_songs_pdf_regeneration, request_pdf_regeneration
from pdf.models.request import AllSongsTemplate, PDFFile
from tenants.utils import tenant_cache_key
from tenants.views import AdminMoveView


def all_songs_defaults(request):
    """Initial values of the all songs PDF of the current tenant."""
    return {
        "filename": "all-songs",
        "locale": request.LANGUAGE_CODE,
        "title": request.tenant.display_name,
    }


class CategoryListView(LocalAdminRequired, ListView):
    """Lists all categories."""

    model = Category
    template_name = "category/list.html"
    context_object_name = "categories"

    def get_queryset(self):
        """Returns the categories of the tenant along with the count of their songs."""
        return (
            super()
            .get_queryset()
            .filter(tenant=self.request.tenant)
            .annotate(song_count=Count("song", filter=Q(song__archived=False)))
            .annotate(file_count=Count("pdffile"))
        )

    def get_context_data(self, **kwargs):
        """Adds the all songs template of the tenant with its song and file counts."""
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        all_songs = AllSongsTemplate.for_tenant(tenant, **all_songs_defaults(self.request))
        all_songs.song_count = all_songs.songs().count()
        all_songs.file_count = all_songs.pdffile_set.count()
        context["all_songs"] = all_songs
        return context


class CategoryCreateView(LocalAdminRequired, PassRequestToFormMixin, UniversalCreateView):
    """Create new category."""

    form_class = CategoryForm
    model = Category
    success_url = reverse_lazy("category:list")

    def get_initial(self):
        """Returns the defaults of a new category in the current language."""
        with translation.override(get_language()):
            return {
                "tenant": self.request.tenant,
                "filename": gettext("songbook"),
                "locale": self.request.LANGUAGE_CODE,
            }


class CategoryUpdateView(LocalAdminRequired, PassRequestToFormMixin, RegenerateViewMixin, UniversalUpdateView):
    """Updates category."""

    form_class = CategoryForm
    model = Category
    success_url = reverse_lazy("category:list")

    def post(self, request, *args, **kwargs):
        """Saves the category and schedules its PDF regeneration when it generates one."""
        response = super().post(request, *args, **kwargs)
        if self.regenerate and self.object.generate_pdf:
            request_pdf_regeneration(self.object)
        return response


class AllSongsUpdateView(LocalAdminRequired, RegenerateViewMixin, UniversalUpdateView):
    """Updates the all songs PDF of the current tenant."""

    form_class = AllSongsForm
    model = AllSongsTemplate
    success_url = reverse_lazy("category:list")
    title_message = _("Update the All Songs PDF")
    success_message = _("The All Songs PDF was successfully updated")

    def get_object(self, queryset=None):
        """Returns the all songs template of the tenant."""
        return AllSongsTemplate.for_tenant(self.request.tenant, **all_songs_defaults(self.request))

    def post(self, request, *args, **kwargs):
        """Saves the template and schedules the PDF regeneration of all songs when asked to."""
        response = super().post(request, *args, **kwargs)
        if self.regenerate:
            request_all_songs_pdf_regeneration(self.object.tenant)
        return response


class CategoryDeleteView(LocalAdminRequired, UniversalDeleteView):
    """Removes category."""

    model = Category
    success_url = reverse_lazy("category:list")


class CategoryMoveView(AdminMoveView):
    """Moves Categories to a different Tenant."""

    formset_form = NameForm
    model = Category

    def action(self, target, ids):
        """What should happen on POST with data from forms."""
        categories = Category.objects.filter(id__in=ids)
        songs = Song.objects.filter(categories__id__in=ids).distinct()
        # Categories are PDFTemplates themselves, so only their files have to follow them
        files = PDFFile.objects.filter(template_id__in=ids)
        # bulk_update sends no signals, so the lists of the source tenants are cleared by hand
        source_tenants = {category.tenant for category in categories.select_related("tenant")}
        touch_songs(songs)
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
