from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Window, F
from django.db.models.functions import Rank
from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404
# Create your views here.
from django.urls import reverse
from django.utils.translation import gettext_lazy

from django.core.cache import cache
from backend.forms import SongForm
from backend.models import Song


def index(request):
    locale = request.LANGUAGE_CODE
    songs = cache.get("songs-%s" % locale, default=Song.objects.filter(locale=locale).annotate(
            song_number=Window(
                expression=Rank(),
                partition_by=[F('locale')],
                order_by=F('id').asc()
            )).order_by("song_number"), version=None)
    return render(request, 'chords/index.html', {'songs': songs})


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
            expire_view_cache("chords:index")
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


def expire_view_cache(view_name, namespace=None, method="GET"):
    """
    This function allows you to invalidate any item from the per-view cache.
    It probably won't work with things cached using the per-site cache
    middleware (because that takes account of the Vary: Cookie header).
    This assumes you're using the Sites framework.
    Arguments:
        * path: The URL of the view to invalidate, like `/blog/posts/1234/`.
        * key prefix: The same as that used for the cache_page()
          function/decorator (if any).

    """
    from django.http import HttpRequest
    from django.utils.cache import get_cache_key
    from django.core.cache import cache
    request = HttpRequest()
    request.method = method
    # Loookup the request path:
    if namespace:
        view_name = namespace + ":" + view_name
    request.path = reverse(view_name)
    # get cache key, expire if the cached item exists:
    cache.clear()
    return False
