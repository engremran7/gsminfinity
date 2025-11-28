from __future__ import annotations

import os
import django
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.ads.models import AdPlacement, AdCreative, Campaign, PlacementAssignment
from apps.site_settings.models import SiteSettings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gsminfinity.settings")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret")
django.setup()


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"], ROOT_URLCONF="gsminfinity.urls", SECURE_SSL_REDIRECT=False)
class AdsApiTests(TestCase):
    def setUp(self) -> None:
        ss = SiteSettings.get_solo()
        ss.ads_enabled = True
        ss.save()
        self.client = Client()

    def test_fill_ad_disabled_returns_403(self):
        ss = SiteSettings.get_solo()
        ss.ads_enabled = False
        ss.save()
        url = reverse("ads:fill_ad")
        res = self.client.get(url, {"placement": "missing"})
        self.assertEqual(res.status_code, 403)

    def test_fill_ad_returns_creative(self):
        campaign = Campaign.objects.create(name="C1")
        placement = AdPlacement.objects.create(
            name="Top",
            slug="top",
            code="top",
            allowed_types="banner",
            allowed_sizes="300x250",
            page_context="blog_detail",
        )
        creative = AdCreative.objects.create(
            campaign=campaign,
            name="Banner",
            creative_type="banner",
            image_url="https://example.com/banner.png",
            click_url="https://example.com",
        )
        PlacementAssignment.objects.create(placement=placement, creative=creative)
        url = reverse("ads:fill_ad")
        res = self.client.get(url, {"placement": placement.slug})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["creative"]["creative"], creative.id)

    def test_click_requires_consent(self):
        placement = AdPlacement.objects.create(
            name="Top",
            slug="top",
            code="top",
            allowed_types="banner",
            allowed_sizes="300x250",
            page_context="blog_detail",
        )
        url = reverse("ads:record_click")
        res = self.client.post(url, {"placement": placement.slug})
        self.assertEqual(res.status_code, 200)
        self.assertIn("skipped", res.json())
