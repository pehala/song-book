"""The reader's translations: the `djangojs` gettext catalogue, one JSON object per language"""

from functools import cache

from django.conf import settings
from django.utils.translation.trans_real import DjangoTranslation

# The reader's strings are English in the source, so English needs no catalogue
SOURCE_LANGUAGE = "en"


@cache
def reader_catalogues():
    """
    Maps each language that translates the reader to `{msgid: translation}`; read from disk once per process.

    Only the project's own catalogue is read and Django's fallback to the default language is left out,
    so a language without translations is absent instead of showing the default language's strings.
    """
    catalogues = {}
    for code, _name in settings.LANGUAGES:
        if code == SOURCE_LANGUAGE:
            continue
        translation = DjangoTranslation(code, domain="djangojs", localedirs=settings.LOCALE_PATHS)
        catalogue = {msgid: text for msgid, text in translation._catalog.items() if msgid and isinstance(msgid, str)}
        if catalogue:
            catalogues[code] = catalogue
    return catalogues
