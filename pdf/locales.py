"""Utils module for locale manipulation"""

import locale
from contextlib import contextmanager

LANG_TO_LOCALE = {
    "en": "en_US.UTF8",
    "cs": "cs_CZ.UTF8",
}


def lang_to_locale(language_code):
    """Transforms django locale into normal locale"""
    return LANG_TO_LOCALE.get(language_code)


@contextmanager
def changed_locale(new_locale):
    """Context manager for temporarily changing locale"""
    old_locale = locale.getlocale(locale.LC_COLLATE)
    try:
        locale.setlocale(locale.LC_COLLATE, new_locale)
        yield
    finally:
        locale.setlocale(locale.LC_COLLATE, old_locale)
