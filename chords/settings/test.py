"""Settings for testing — overrides production cache with in-memory backend."""

from chords.settings.base import *  # noqa: F403

SECRET_KEY = "test-secret-key-not-for-production"

ALLOWED_HOSTS = ["localhost", "other.localhost", "testserver"]

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

# Run Huey tasks synchronously in the same process — no worker needed
HUEY = {"immediate": True}

# Keep the production-style delay so editing songs in tests never renders a PDF inline
CATEGORY_PDF_DELAY = 30 * 60

# The default PBKDF2 hasher runs 1.5M iterations, around 200 ms per user created, and
# almost every test creates one. The tests sign in through force_login(), never through
# a password, so hash strength buys nothing here.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
