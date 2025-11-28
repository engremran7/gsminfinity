from __future__ import annotations

import os
import django
from django.test import TestCase, override_settings
from django.template import Context, Template

from apps.core.utils import feature_flags
from apps.site_settings.models import SiteSettings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gsminfinity.settings")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret")
django.setup()


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost"],
    ROOT_URLCONF="gsminfinity.urls",
    TEMPLATES=[{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}],
)
class SeoTemplateTagTests(TestCase):
    def test_render_seo_meta_respects_flag(self):
        ss = SiteSettings.get_solo()
        ss.seo_enabled = False
        ss.save()
        tpl = Template("{% load seo_tags %}{% render_seo_meta obj %}")
        out = tpl.render(Context({"obj": None}))
        self.assertEqual(out.strip(), "")
