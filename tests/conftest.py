"""Shared pytest fixtures for the whole test suite."""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.test import Client
from django.utils.timezone import now
from huey.contrib.djhuey import HUEY

from backend.models import Song
from category.models import Category
from pdf.models import Status
from pdf.models.request import ManualPDFTemplate, PDFFile, PDFSong
from tenants.models import Tenant

REAL_ON_COMMIT = transaction.on_commit


@pytest.fixture(autouse=True)
def run_on_commit_at_once(monkeypatch):
    """The test's own transaction never commits, so callbacks that wait for the commit run straight away"""
    monkeypatch.setattr(transaction, "on_commit", lambda func, using=None, robust=False: func())


@pytest.fixture
def real_on_commit(monkeypatch):
    """Restores the deferral, for tests of what waits for a commit"""
    monkeypatch.setattr(transaction, "on_commit", REAL_ON_COMMIT)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def flush_huey():
    """Keeps tasks enqueued by one test from leaking into the next one"""
    HUEY.storage.flush_all()
    yield
    HUEY.storage.flush_all()


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Redirects uploads and generated PDFs away from the source tree"""
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture
def tenant(db):
    # The initial migration already creates a Tenant with hostname=TENANT_HOSTNAME
    # ("localhost" in base settings). Use get_or_create to avoid UNIQUE violations.
    obj, _ = Tenant.objects.get_or_create(
        hostname="localhost",
        defaults={
            "name": "Test",
            "display_name": "Test Songbook",
            "index_redirect": "/all",
        },
    )
    return obj


@pytest.fixture
def other_tenant(db):
    """A second Tenant, used to prove that data does not leak between them"""
    return Tenant.objects.create(
        hostname="other.localhost",
        name="Other",
        display_name="Other Songbook",
        index_redirect="/all",
    )


@pytest.fixture
def make_category(db):
    """Factory for Categories, defaults are enough to generate a PDF from"""

    def factory(tenant, **kwargs):
        kwargs.setdefault("name", "Test Category")
        kwargs.setdefault("slug", "test-cat")
        kwargs.setdefault("generate_pdf", False)
        kwargs.setdefault("filename", "songbook")
        kwargs.setdefault("locale", "en")
        return Category.objects.create(tenant=tenant, **kwargs)

    return factory


@pytest.fixture
def category(tenant, make_category):
    return make_category(tenant)


@pytest.fixture
def other_category(other_tenant, make_category):
    return make_category(other_tenant, name="Other Category", slug="other-cat")


@pytest.fixture
def make_song(db):
    """Factory for Songs, optionally attached to categories"""

    def factory(*categories, **kwargs):
        kwargs.setdefault("name", "Test Song")
        kwargs.setdefault("text", "{Ami}Hello {C}World")
        song = Song.objects.create(**kwargs)
        song.categories.add(*categories)
        return song

    return factory


@pytest.fixture
def song(category, make_song):
    return make_song(category)


@pytest.fixture
def archived_song(category, make_song):
    return make_song(category, name="Archived Song", text="x", archived=True)


@pytest.fixture
def manual_template(tenant, song):
    """A ManualPDFTemplate holding a single numbered song"""
    template = ManualPDFTemplate.objects.create(
        tenant=tenant,
        name="Manual Template",
        filename="manual",
        locale="en",
    )
    PDFSong.objects.create(request=template, song=song, song_number=1)
    return template


@pytest.fixture
def pdf_file(tenant, category):
    """A PDFFile awaiting generation, created from the category template"""
    return PDFFile.objects.create(
        tenant=tenant,
        template=category,
        filename="songbook",
        status=Status.QUEUED,
        update_date=now(),
    )


@pytest.fixture
def superuser(db):
    User = get_user_model()
    return User.objects.create_superuser(username="super", password="pass")


@pytest.fixture
def staff_user(tenant):
    User = get_user_model()
    user = User.objects.create_user(username="staff", password="pass")
    tenant.admins.add(user)
    return user


@pytest.fixture
def plain_user(db):
    """A logged in user without any administrative rights"""
    User = get_user_model()
    return User.objects.create_user(username="plain", password="pass")


@pytest.fixture
def anon_client(db):
    return Client(HTTP_HOST="localhost")


@pytest.fixture
def superuser_client(superuser):
    c = Client(HTTP_HOST="localhost")
    c.force_login(superuser)
    return c


@pytest.fixture
def staff_client(staff_user):
    c = Client(HTTP_HOST="localhost")
    c.force_login(staff_user)
    return c


@pytest.fixture
def plain_client(plain_user):
    c = Client(HTTP_HOST="localhost")
    c.force_login(plain_user)
    return c
