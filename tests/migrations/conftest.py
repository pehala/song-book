"""Fixtures for migration tests: the real migrations, run against a scratch database.

A test module names the migrations it covers by overriding `migration_target`, and inserts the rows it wants
migrated by overriding `create_old_data`, which runs with the schema as it was at the source migration. The
migration itself runs once, after that, so every test in the module sees the migrated database.

The scratch database is empty, so only the migrations the source one depends on have run when the old rows are
inserted: they are made with the models of that state, which `rows` gives. It takes the place of the default
connection for the module, because older migrations query it without naming one; the test database is left alone.
"""

import copy

import pytest
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor
from django.db.utils import load_backend


@pytest.fixture(scope="module")
def migration_connection(django_db_blocker):
    """Yield a connection to an empty scratch database, which is the default one while a module runs."""
    original = connections[DEFAULT_DB_ALIAS]
    settings = copy.deepcopy(original.settings_dict)
    settings["NAME"] = ":memory:"
    scratch = load_backend(settings["ENGINE"]).DatabaseWrapper(settings, DEFAULT_DB_ALIAS)
    connections[DEFAULT_DB_ALIAS] = scratch
    with django_db_blocker.unblock():
        yield scratch
        scratch.close()
    connections[DEFAULT_DB_ALIAS] = original


@pytest.fixture(scope="module")
def schema():
    """Hold the apps of the state the scratch database was last migrated to."""
    return {}


@pytest.fixture(scope="module")
def migrate(migration_connection, schema):
    """Return `migrate(node)`, which migrates to `(app, name)` and returns the apps of that state."""

    def run(node):
        executor = MigrationExecutor(migration_connection)
        executor.migrate([node])
        schema["apps"] = executor.loader.project_state([node]).apps
        return schema["apps"]

    return run


@pytest.fixture(scope="module")
def rows(schema):
    """Return `rows("app.Model")`, a queryset of the model as the scratch database has it right now."""

    def get(label):
        return schema["apps"].get_model(label).objects.all()

    return get


@pytest.fixture(scope="module")
def migration_target() -> tuple[tuple[str, str], tuple[str, str]]:
    """Return the (source, target) migrations a module tests, each as `(app, name)`; override per module."""
    raise NotImplementedError


@pytest.fixture(scope="module")
def migrate_to_start(migrate, migration_target):
    """Migrate the empty database to the source migration."""
    migrate(migration_target[0])


@pytest.fixture(scope="module")
def create_old_data(migrate_to_start):
    """Insert the rows to be migrated, at the source migration; override per module."""


@pytest.fixture(scope="module", autouse=True)
def migrate_to_end(create_old_data, migrate, migration_target):
    """Run the migration under test."""
    migrate(migration_target[1])
