from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.utils.translation import gettext_lazy as _


from backend.views import SongListView
from category.forms import CategoryForm
from category.models import Category


class CategorySongsListView(SongListView):

    def get_queryset(self):
        slug = self.kwargs['slug']
        if not Category.objects.filter(slug=slug).exists():
            raise Http404(_("Category on url /%(slug)s does not exists") % {'slug': slug})
        return super().get_queryset() \
            .filter(categories__slug=slug)


@method_decorator(login_required, name='dispatch')
class CategoryListView(ListView):
    model = Category
    template_name = "category/list.html"
    context_object_name = "categories"


@method_decorator(login_required, name='dispatch')
class CategoryCreateView(SuccessMessageMixin, CreateView):
    form_class = CategoryForm
    model = Category
    template_name = 'category/add.html'
    success_url = reverse_lazy("category:list")
    success_message = _("Category %(name)s was successfully created")


@method_decorator(login_required, name='dispatch')
class CategoryUpdateView(SuccessMessageMixin, UpdateView):
    form_class = CategoryForm
    model = Category
    template_name = 'category/add.html'
    success_url = reverse_lazy("category:list")
    success_message = _("Category %(name)s was successfully updated")


@method_decorator(login_required, name='dispatch')
class CategoryDeleteView(SuccessMessageMixin, DeleteView):
    model = Category
    template_name = "category/confirm_delete.html"
    success_url = reverse_lazy("category:list")
    success_message = _("Category %(name)s was successfully deleted")

