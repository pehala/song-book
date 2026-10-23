"""Settings for production"""
# pylint: disable=unused-wildcard-import,wildcard-import
from .base import *

# Every tenant hostname served by this instance, plus the scheme-qualified origins for CSRF
ALLOWED_HOSTS = ["localhost", "0.0.0.0"]
CSRF_TRUSTED_ORIGINS = ["https://localhost"]
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "$sr-v9zx(s!!q)6*2!1#t_+-z5ku*$+=edf*gstxjwz3opj94n"

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG also disables content-hashed static URLs, so a deploy would leave browsers with stale files.
# nginx has to serve /media/ itself once this is off (Django serves it only in DEBUG).
DEBUG = False

# Serve the prerendered html column instead of rendering markdown on every request;
# USE_DYNAMIC_PRERENDER fills rows that are still empty (the deploy target runs `prerender` anyway).
USE_PRERENDERED_MARKDOWN = True
USE_DYNAMIC_PRERENDER = True

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379?db=2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

HUEY = {"immediate": True}

# pool = ConnectionPool(host="localhost", port=6379, max_connections=20, db=2)
# HUEY = RedisHuey("default", connection_pool=pool)
