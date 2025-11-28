import os

import django
from django.conf import settings


def pytest_configure():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gsminfinity.settings")
    os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret")
    if not settings.configured:
        django.setup()
