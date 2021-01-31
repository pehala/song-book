from django.core.management import BaseCommand

from backend.models import Song


class Command(BaseCommand):
    def handle(self, *args, **options):
        Song.objects.all().update(prerendered_pdf=None, prerendered_web=None)
        print("Removed all prerendered markdowns")
