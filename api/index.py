"""
Vercel entrypoint: runs the Django backend as one Python serverless function.

vercel.json rewrites /api/*, /admin* and /static/* here; Django's own URL
configuration (backend/config/urls.py) then routes the request as usual.
The React build in frontend/dist is served as static files for every other path.
"""
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402  (needs sys.path and the env var first)

app = get_wsgi_application()
