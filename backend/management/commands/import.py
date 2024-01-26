"""Management command for importing Songs"""

import json
import logging
from argparse import ArgumentParser
from pathlib import Path

from django.core.management import BaseCommand
from django.db import transaction

from backend.models import Song
from category.models import Category

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    """Imports Songs from a JSON"""

    help = "Imports Songs from JSON"

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
            "-c",
            "--category",
            required=True,
            type=int,
            help="ID of a target category",
        )
        parser.add_argument("input", type=Path, help="Input JSON file")

    def handle(self, *args, **options):
        category = Category.objects.get(id=options["category"])

        with open(options["input"], encoding="UTF-8") as file:
            imported = json.load(file)

        with transaction.atomic():
            songs = Song.objects.bulk_create(Song(**song) for song in imported)
            for song in songs:
                song.categories.add(category)
