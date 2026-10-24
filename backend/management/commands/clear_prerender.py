"""Clear prerender command"""

from django.core.management import BaseCommand

from backend.cache import touch_songs
from backend.models import Song


class Command(BaseCommand):
    """Erases all prerendered html from all songs"""

    def handle(self, *args, **options):
        Song.objects.all().update(prerendered=None)
        touch_songs(Song.objects.all())
        print("Removed all prerendered markdowns")
