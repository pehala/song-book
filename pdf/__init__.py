"""Initialize PDF module, specifically create media directory if it doesn't exist"""

from pathlib import Path

from django.conf import settings

Path(f"{settings.MEDIA_ROOT}/{settings.PDF_FILE_DIR}").mkdir(parents=True, exist_ok=True)
