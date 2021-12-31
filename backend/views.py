"""Views for backend app"""
import json
from typing import Dict
import zipfile
import xml.etree.ElementTree as ET

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.forms import model_to_dict
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _, gettext_noop
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, FormView
from django_datatables_view.base_datatable_view import BaseDatatableView

from analytics.views import AnalyticsMixin
from backend.forms import SongForm, UploadFileForm
from backend.models import Song
from backend.utils import regenerate_pdf, regenerate_prerender
from category.models import Category


def transform_song(song: Song, number: int, authenticated: bool) -> Dict:
    """Transforms song into a dict representation"""
    transformed = model_to_dict(song, ["id", "name", "capo", "author", "link"])
    transformed["number"] = number
    if authenticated:
        transformed['edit_url'] = reverse("chords:edit", kwargs={"pk": song.id})
        transformed['delete_url'] = reverse("chords:delete", kwargs={"pk": song.id})
    transformed["text"] = song.rendered_web_markdown
    return transformed


class SongListView(ListView):
    """Lists songs in the one page application"""
    model = Song
    template_name = 'songs/index.html'
    context_object_name = 'songs'

    FIELDS = ["id", "name", "capo", "author", "link", "prerendered_web"]

    def get_context_data(self, *, object_list=None, **kwargs):
        context_data = super().get_context_data(object_list=object_list, **kwargs)
        authenticated = self.request.user.is_authenticated

        songs = []

        for i, song in enumerate(context_data["songs"]):
            songs.append(transform_song(song, i + 1, authenticated))

        context_data['songs'] = json.dumps(songs, cls=DjangoJSONEncoder)
        return context_data


class IndexSongListView(SongListView, AnalyticsMixin):
    """Shows first available category"""
    KEY = gettext_noop("Index Page")

    def get_queryset(self):
        if Category.objects.count() > 0:
            slug = settings.DEFAULT_CATEGORY
            if slug and Category.objects.filter(slug=slug).exists():
                category = Category.objects.get(slug=slug)
            else:
                category = Category.objects.all()[0]
            return super().get_queryset().filter(categories__slug=category.slug)
        return super().get_queryset()


@method_decorator(login_required, name='dispatch')
class SongCreateView(SuccessMessageMixin, CreateView):
    """Creates new song"""
    form_class = SongForm
    model = Song
    template_name = 'songs/add.html'
    success_message = _("Song %(name)s was successfully created")
    success_url = reverse_lazy("backend:index")

    def get_success_url(self):
        regenerate_pdf(self.object)
        regenerate_prerender(self.object)
        return super().get_success_url()


@method_decorator(login_required, name='dispatch')
class SongUpdateView(SuccessMessageMixin, UpdateView):
    """Updates existing song"""
    form_class = SongForm
    model = Song
    template_name = 'songs/add.html'
    success_url = reverse_lazy("backend:index")
    success_message = _("Song %(name)s was successfully updated")

    def form_valid(self, form):
        if len(form.changed_data) > 0:
            regenerate_pdf(self.object, True)
            regenerate_prerender(self.object)
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class SongDeleteView(DeleteView):
    """Removes song"""
    model = Song
    template_name = "songs/confirm_delete.html"
    success_url = reverse_lazy("backend:index")
    success_message = _("Song %s was successfully deleted")

    def delete(self, request, *args, **kwargs):
        regenerate_pdf(self.get_object())
        response = super().delete(request, *args, **kwargs)
        messages.success(self.request, self.success_message % self.object.name)
        return response


@method_decorator(login_required, name='dispatch')
class SongsDatatableView(BaseDatatableView):
    """API for datatables that returns all songs"""
    model = Song
    max_display_length = 500
    columns = ["name", "author", "capo"]


def quelea_song_import(cleaned_data):
    """Read data from file in cleaned_data, and import all songs in qsp archive"""

    with zipfile.ZipFile(cleaned_data['file']) as file:
        songs = {name: file.read(name) for name in file.namelist()}

    lyrics = []

    for name in songs.keys():
        song = ET.fromstring(songs[name])
        lyrics_lines = []
        for child in song.findall('.//lyrics'):
            if child.text is not None:
                lyrics_lines.append(child.text)

        lyrics.append((name, '\n\n'.join(lyrics_lines)))

    num_songs = 0

    for (name, text) in lyrics:
        clean_name = name.rstrip('.xml')

        song_obj = Song(name=clean_name, text=text)
        song_obj.save()

        list_ids = [f.pk for f in cleaned_data['categories']]

        song_obj.categories.set(list_ids)
        regenerate_pdf(song_obj)
        regenerate_prerender(song_obj)
        num_songs += 1

    return num_songs


@method_decorator(login_required, name='dispatch')
class UploadView(FormView):
    """View to recieve qsp file and import all songs"""

    form_class = UploadFileForm
    template_name = 'songs/import.html'

    success_url = reverse_lazy('backend:index')

    # def get_success_url(self):
    #     regenerate_pdf(self.object)
    #     regenerate_prerender(self.object)
    #     return super().get_success_url()

    def form_valid(self, form):
        num = quelea_song_import(form.cleaned_data)
        messages.success(self.request, f"{num} songs imported.")
        return super().form_valid(form)

