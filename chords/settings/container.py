"""Settings for the container image, configured through environment variables.

PostgreSQL and Redis are reached over unix sockets mounted into the container; see docs/DEPLOY.md.
"""

import os

from chords.settings.base import *  # noqa: F403


def env_list(name):
    """Comma separated environment variable as a list"""
    return [item.strip() for item in os.environ.get(name, "").split(",") if item.strip()]


DEBUG = False
SECRET_KEY = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# TLS is terminated by nginx, which passes the original scheme in X-Forwarded-Proto
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        # A directory as HOST makes psycopg connect to the unix socket inside it
        "HOST": os.environ.get("POSTGRES_SOCKET_DIR", "/run/postgresql"),
        "NAME": os.environ.get("POSTGRES_DB", "songbook"),
        "USER": os.environ.get("POSTGRES_USER", "songbook"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        # The port is part of the socket's file name (.s.PGSQL.<port>); empty means PostgreSQL's default, 5432
        "PORT": os.environ.get("POSTGRES_PORT", ""),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

REDIS_SOCKET = os.environ.get("REDIS_SOCKET", "/run/redis/redis.sock")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"unix://{REDIS_SOCKET}?db=0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Huey lives in its own Redis database, so clearing the cache never drops queued PDF jobs
HUEY = {
    "name": "songbook",
    "immediate": False,
    "connection": {"url": f"unix://{REDIS_SOCKET}?db=1"},
}

MEDIA_ROOT = os.environ["MEDIA_ROOT"]

TENANT_HOSTNAME = os.environ.get("TENANT_HOSTNAME", TENANT_HOSTNAME)  # noqa: F405
SITE_NAME = os.environ.get("SITE_NAME", SITE_NAME)  # noqa: F405

# Dotted path of the renderer of the songs, e.g. chords.markdown.RUBY_RENDERER; the preview of the editor follows it
SONG_RENDERER = os.environ.get("SONG_RENDERER", SONG_RENDERER)  # noqa: F405
MARKDOWNX_MARKDOWNIFY_FUNCTION = SONG_RENDERER

# The web container prerenders every song on start (make prerender); edits re-render the edited song
USE_PRERENDERED_MARKDOWN = True
USE_DYNAMIC_PRERENDER = True
