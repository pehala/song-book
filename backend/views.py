from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Window, F
from django.db.models.aggregates import Sum
from django.db.models.functions import DenseRank, Rank
from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404
# Create your views here.
from django.utils.translation import gettext_lazy
from rest_framework import status
from django.conf import settings

from backend.forms import SongForm
from backend.models import Song


def index(request):
    songs = Song.objects.filter(locale=request.LANGUAGE_CODE).order_by("-date").annotate(
            song_number=Window(
                expression=Rank(),
                partition_by=[F('locale')],
                order_by=F('id').asc()
            ))
    return render(request, 'chords/index.html', {'songs': songs})


@login_required
def add(request):
    return render(request, 'chords/add.html', {'form': SongForm()})


@login_required
def edit(request, pk):
    if pk:
        song = get_object_or_404(Song, pk=pk)
    else:
        song = Song(locale=request.LANGUAGE_CODE)

    form = SongForm(request.POST or None, instance=song)
    if request.POST:
        if form.is_valid():
            song = form.save()

            if pk:
                text = gettext_lazy("Song with id %(id)s was successfully edited")
            else:
                text = gettext_lazy("Song with id %(id)s was successfully created")

            messages.success(request, text % {'id': song.id})
            # Save was successful, so redirect to another page
            return redirect('chords:index')
        else:
            return HttpResponseBadRequest()

    return render(request, 'chords/add.html', {'form': form})


def delete(request, pk):
    song = Song.objects.get(pk=pk)
    if song is not None:
        song.delete()
        return redirect('chords:index')
    else:
        return HttpResponseNotFound()
