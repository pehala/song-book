"""Prerender command."""

from cached_markdown_field.prerender import prerender
from django.core.management import BaseCommand
from django.db import transaction

from backend.cache import touch_songs
from backend.models import Song


class Command(BaseCommand):
    """Generates prerendered html from markdown for all songs."""

    def handle(self, *args, **options):
        """Renders every song again, stores the HTML that changed and marks those songs as changed.

        Both happen in one transaction, so a run that fails stores nothing and the next one starts over.
        """
        with transaction.atomic():
            changed = prerender(Song.objects.all())
            touch_songs(Song.objects.filter(pk__in=[song.pk for song in changed]))
        print(f"Prerendered all songs, {len(changed)} changed")
