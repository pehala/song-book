from django.core.cache import cache

from django.db.models import Window, F
from django.db.models.functions import Rank

from backend.models import Song


def fetch_all_songs(locale):
    songs = Song.objects.filter(locale=locale).annotate(
        song_number=Window(
            expression=Rank(),
            partition_by=[F('locale')],
            order_by=F('id').asc()
        )).order_by("song_number")
    return songs
