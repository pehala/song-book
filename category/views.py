"""Views for categories"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _


from backend.views import SongListView
from category.forms import CategoryForm
from category.models import Category


class CategorySongsListView(SongListView):
    """Shows all songs in a category"""
    def get_queryset(self):
        slug = self.kwargs['slug']
        if not Category.objects.filter(slug=slug).exists():
            raise Http404(_("Songbook on url /%(slug)s does not exists") % {'slug': slug})
        return super().get_queryset() \
            .filter(categories__slug=slug)


@method_decorator(login_required, name='dispatch')
class CategoryListView(ListView):
    """Lists all categories"""
    model = Category
    template_name = "category/list.html"
    context_object_name = "categories"


@method_decorator(login_required, name='dispatch')
class CategoryCreateView(SuccessMessageMixin, CreateView):
    """Create new category"""
    form_class = CategoryForm
    model = Category
    template_name = 'category/add.html'
    success_url = reverse_lazy("category:list")
    success_message = _("Songbook %(name)s was successfully created")

    def get_success_message(self, cleaned_data):
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return super().get_success_message(cleaned_data)


@method_decorator(login_required, name='dispatch')
class CategoryUpdateView(SuccessMessageMixin, UpdateView):
    """Updates category"""
    form_class = CategoryForm
    model = Category
    template_name = 'category/add.html'
    success_url = reverse_lazy("category:list")
    success_message = _("Songbook %(name)s was successfully updated")

    def get_success_message(self, cleaned_data):
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return super().get_success_message(cleaned_data)


@method_decorator(login_required, name='dispatch')
class CategoryDeleteView(DeleteView):
    """Removes category"""
    model = Category
    template_name = "category/confirm_delete.html"
    success_url = reverse_lazy("category:list")
    success_message = _("Songbook %(name)s was successfully deleted")

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(self.request, self.success_message % obj.__dict__)
        response = super().delete(request, *args, **kwargs)
        cache.delete(settings.CATEGORY_CACHE_KEY)
        return response
