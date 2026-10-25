"""Static files storage."""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class ManifestStorage(ManifestStaticFilesStorage):
    """Content-hashed static files whose ES module imports are rewritten too.

    An `import x from "./y.js"` inside a hashed module points at the hashed file, so the
    10-year cache never serves a stale module after a deploy.
    """

    support_js_module_import_aggregation = True
