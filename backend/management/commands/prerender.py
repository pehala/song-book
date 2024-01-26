"""Prerender command"""

from django.core.management import BaseCommand

from backend.models import Song


class Command(BaseCommand):
    """Generates prerendered html from markdown for all songs"""

    def handle(self, *args, **options):
        bulk = []
        for song in Song.objects.all():
            print(f"Prerendering song {song.name}")
            song.prerender(save=False)
            bulk.append(song)
        print("Updating database fields")
        Song.objects.bulk_update(bulk, ["prerendered"])
        print("Prerendered all songs")
