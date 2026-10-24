"""Prerender command"""

from django.core.management import BaseCommand

from backend.cache import touch_songs
from backend.models import Song


class Command(BaseCommand):
    """Generates prerendered html from markdown for all songs"""

    def handle(self, *args, **options):
        changed = []
        for song in Song.objects.all():
            print(f"Prerendering song {song.name}")
            before = song.prerendered
            song.prerender(save=False)
            if song.prerendered != before:
                changed.append(song)
        print("Updating database fields")
        Song.objects.bulk_update(changed, ["prerendered"])
        touch_songs(Song.objects.filter(pk__in=[song.pk for song in changed]))
        print("Prerendered all songs")
