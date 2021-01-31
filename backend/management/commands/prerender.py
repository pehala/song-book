from django.core.management import BaseCommand

from backend.models import Song


class Command(BaseCommand):
    def handle(self, *args, **options):
        for song in Song.objects.all():
            print(f"Prerendering song {song.name}")
            song.prerender_all()
        print("Prerendered all songs")
