"""Settings for production"""
# pylint: disable=unused-wildcard-import,wildcard-import
from .base import *

ALLOWED_HOSTS = ["localhost", "0.0.0.0"]
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "$sr-v9zx(s!!q)6*2!1#t_+-z5ku*$+=edf*gstxjwz3opj94n"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379?db=2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}
