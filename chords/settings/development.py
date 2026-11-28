"""Settings for local development: SQLite, an in-memory cache and DEBUG, so nothing has to be generated or collected.

Used by `make dev`. The database is `db.sqlite3` of the working tree, as in `base.py`,
unless the `DB_FILE` environment variable names another file.
"""

import os
from pathlib import Path

from chords.settings.base import *  # noqa: F403

SECRET_KEY = "development-secret-key-not-for-production"
ALLOWED_HOSTS = ["*"]

if "DB_FILE" in os.environ:
    DATABASES["default"]["NAME"] = Path(os.environ["DB_FILE"]).expanduser()  # noqa: F405

# DEBUG serves the static files unhashed, straight from the source tree, and Django serves /media/ itself
DEBUG = True

# Generate PDFs inline instead of needing a worker
HUEY = {"immediate": True}
