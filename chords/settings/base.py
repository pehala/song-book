"""
Django settings for chords project.

Generated by 'django-admin startproject' using Django 2.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# Application definition

INSTALLED_APPS = [
    "frontend",
    "category",
    "backend",
    "pdf",
    "analytics",
    "tenants",
    "django_bootstrap5",
    "sass_processor",
    "markdownx",
    "menu",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "debug_toolbar",
    "django_rq",
]

MARKDOWNX_MARKDOWNIFY_FUNCTION = "chords.markdown.RENDERER"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # 'django.middleware.cache.UpdateCacheMiddleware',
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # 'django.middleware.cache.FetchFromCacheMiddleware',
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "backend.middleware.settings.SiteNameMiddleware",
    "tenants.middleware.RecognizeTenantMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "chords.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "sass_processor.finders.CssFinder",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

COMPRESS_ENABLED = True
SASS_PRECISION = 8
SASS_OUTPUT_STYLE = "compact"
STATIC_ROOT = "chords/static/"

WSGI_APPLICATION = "chords.wsgi.application"


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "../db.sqlite3"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = "cs"

LANGUAGES = (
    ("en", "English"),
    ("cs", "Česky"),
)

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "chords",
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = "/static/"

LOGOUT_REDIRECT_URL = "/"
LOGIN_REDIRECT_URL = "/"

SESSION_COOKIE_AGE = 86400

MEDIA_ROOT = "chords/media"
MEDIA_URL = "/media/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}

# Custom settings
SITE_NAME = "Songbook"
PDF_FILE_DIR = "pdfs"
CACHE_TIMEOUT = 86400


# If true, it will prerender all markdowns on create/update and then use them in fetch requests
USE_PRERENDERED_MARKDOWN = False
# This setting will prerender markdown on fetch request and save it for future use, if it is empty
# might incur performance penalties on production, for production deployment use
USE_DYNAMIC_PRERENDER = False

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Cache keys
PDF_CACHE_KEY = "PDFS"
CATEGORY_CACHE_KEY = "CATEGORIES"
PDF_INCLUDE_LINK = ""

RQ_QUEUES = {
    "default": {
        "USE_REDIS_CACHE": "default",
    },
}

# Default Tenant, only used on migration
TENANT_NAME = "Default"
TENANT_HOSTNAME = "localhost"
