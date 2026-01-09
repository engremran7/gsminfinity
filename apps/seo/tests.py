from __future__ import annotations

import os

import django
from django.template import Context, Template
from django.test import TestCase, override_settings

from apps.site_settings.models import SiteSettings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret")
django.setup()


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost"],
    ROOT_URLCONF="app.urls",
)
class SeoTemplateTagTests(TestCase):
    def test_render_seo_meta_respects_flag(self):
        ss = SiteSettings.get_solo()
        ss.seo_enabled = False
        ss.save()
        tpl = Template("{% load seo_tags %}{% render_seo_meta obj %}")
        out = tpl.render(Context({"obj": None}))
        self.assertEqual(out.strip(), "")
