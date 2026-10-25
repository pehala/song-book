"""Utility functions for backend app"""

import subprocess
from email.utils import parsedate_to_datetime
from functools import cache

from django.conf import settings

from category.utils import request_all_songs_pdf_regeneration, request_pdf_regeneration


def regenerate_pdf(song):
    """Regenerates PDFs for each category song is in and the all songs PDF of their tenants"""
    tenants = {}
    for category in song.categories.select_related("tenant"):
        request_pdf_regeneration(category)
        tenants[category.tenant_id] = category.tenant
    for tenant in tenants.values():
        request_all_songs_pdf_regeneration(tenant)


@cache
def get_version():
    """Returns currently used version e.g. date of the last commit, taken from BUILD_DATE when it is set"""
    if settings.BUILD_DATE:
        return settings.BUILD_DATE
    date = parsedate_to_datetime(
        subprocess.check_output(["git", "--no-pager", "log", "-1", "--format='%aD'"]).decode("ascii").strip()
    )
    return date.strftime("%Y/%m/%d")


@cache
def get_git_revision():
    """Returns sha of the latest revision, taken from BUILD_REVISION when it is set"""
    if settings.BUILD_REVISION:
        return settings.BUILD_REVISION
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("ascii").strip()
