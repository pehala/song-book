"""Every `{% static %}` literal in the templates must name a file the finders can locate."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.staticfiles import finders

STATIC_TAG = re.compile(r"""{%\s*static\s+(['"])(?P<path>[^'"]+)\1""")
ROOT = Path(settings.BASE_DIR).parent


def template_references():
    for template in sorted(ROOT.glob("*/templates/**/*")):
        if template.is_file():
            for match in STATIC_TAG.finditer(template.read_text()):
                yield pytest.param(match["path"], id=f"{template.relative_to(ROOT)}:{match['path']}")


@pytest.mark.parametrize("path", list(template_references()))
def test_static_reference_exists(path):
    """The hashed production storage raises on a missing file, the test storage does not."""
    assert finders.find(path), path
