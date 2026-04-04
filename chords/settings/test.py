"""Settings for testing — overrides production cache with in-memory backend"""

from chords.settings.base import *  # noqa: F401, F403

SECRET_KEY = "test-secret-key-not-for-production"

ALLOWED_HOSTS = ["localhost", "testserver"]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Use plain static files storage so tests don't require a collected manifest
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
