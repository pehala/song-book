"""Utility functions for backend app"""

import subprocess
from email.utils import parsedate_to_datetime
from functools import cache

from django.conf import settings

from category.utils import request_pdf_regeneration


def regenerate_pdf(song):
    """Regenerates PDFs for each category song is in"""
    for category in song.categories.all():
        request_pdf_regeneration(category)


def regenerate_prerender(song):
    """Regenerates prerendered html for song"""
    if settings.USE_PRERENDERED_MARKDOWN:
        song.prerender()


@cache
def get_version():
    """Returns currently used version e.g. date of the last commit"""
    date = parsedate_to_datetime(
        subprocess.check_output(["git", "--no-pager", "log", "-1", "--format='%aD'"]).decode("ascii").strip()
    )
    return date.strftime("%Y/%m/%d")


@cache
def get_git_revision():
    """Returns sha of the latest revision"""
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("ascii").strip()
