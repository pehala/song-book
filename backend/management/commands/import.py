"""Management command for importing Songs."""  # noqa: N999

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
    """Imports Songs from a JSON."""

    help = "Imports Songs from JSON"

    def add_arguments(self, parser: ArgumentParser):
        """Adds the target category and the JSON file to import."""
        parser.add_argument(
            "-c",
            "--category",
            required=True,
            type=int,
            help="ID of a target category",
        )
        parser.add_argument("input", type=Path, help="Input JSON file")

    def handle(self, *args, **options):
        """Imports the songs of the JSON file into the category."""
        category = Category.objects.get(id=options["category"])

        with open(options["input"], encoding="UTF-8") as file:
            imported = json.load(file)

        songs = [Song(**song) for song in imported]

        with transaction.atomic():
            songs = Song.objects.bulk_create(songs)
            for song in songs:
                # adding the category sends m2m_changed, which invalidates the tenant's song lists
                song.categories.add(category)
