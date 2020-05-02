"""Utility functions for backend app"""
from django.db.models import Window, F
from django.db.models.functions import Rank

from backend.models import Song


def fetch_all_songs(locale):
    """Fetches all songs from database and adds song number field to them"""
    songs = Song.objects.filter(locale=locale).annotate(
        song_number=Window(
            expression=Rank(),
            partition_by=[F('locale')],
            order_by=F('id').asc()
        )).order_by("song_number")
    return songs
