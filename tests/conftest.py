"""Shared pytest fixtures for songs JSON endpoint tests."""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client

from backend.models import Song
from category.models import Category
from tenants.models import Tenant


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


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
def category(tenant):
    return Category.objects.create(
        tenant=tenant,
        name="Test Category",
        slug="test-cat",
        generate_pdf=False,
    )


@pytest.fixture
def song(category):
    s = Song.objects.create(name="Test Song", text="{Ami}Hello {C}World")
    s.categories.add(category)
    return s


@pytest.fixture
def archived_song(category):
    s = Song.objects.create(name="Archived Song", text="x", archived=True)
    s.categories.add(category)
    return s


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
