
from __future__ import annotations

from unittest.mock import patch
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.ads.models import AdPlacement, AdCreative, Campaign, PlacementAssignment, AdsSettings
from apps.site_settings.models import SiteSettings
from apps.ads.services.rotation.engine import choose_creative


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost"],
    ROOT_URLCONF="app.urls",
    SECURE_SSL_REDIRECT=False,
)
class AdsApiTests(TestCase):
    def setUp(self) -> None:
        # Ensure SiteSettings exists (for any views that might need it)
        SiteSettings.get_solo()
        # Use AdsSettings to enable/disable ads
        ads_settings = AdsSettings.get_solo()
        ads_settings.ads_enabled = True
        ads_settings.save()
        self.client = Client()

    def test_fill_ad_disabled_returns_403(self):
        ads_settings = AdsSettings.get_solo()
        ads_settings.ads_enabled = False
        ads_settings.save()
        url = reverse("ads:fill_ad")
        res = self.client.get(url, {"placement": "missing"})
        self.assertEqual(res.status_code, 403)

    @patch("apps.ads.views._has_ads_consent", return_value=True)
    def test_fill_ad_returns_creative(self, mock_consent):
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
        # If ok=False, the response has an error structure
        if payload.get("ok", True) is False:
            self.fail(f"fill_ad failed: {payload.get('error')}")
        self.assertIn("creative", payload, f"Expected 'creative' in payload, got: {payload}")
        # creative is a dict with the creative details including 'creative' ID
        creative_data = payload["creative"]
        self.assertEqual(creative_data["creative"], creative.id)
        self.assertEqual(creative_data["type"], "banner")

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

    def test_rotation_allows_string_true_consent(self):
        campaign = Campaign.objects.create(name="C1", type="direct")
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
        context = {"consent_ads": "1", "page_context": placement.page_context}
        selected = choose_creative(placement, context)
        self.assertIsNotNone(selected)

    def test_rotation_blocks_string_false_consent(self):
        campaign = Campaign.objects.create(name="C1", type="direct")
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
        context = {"consent_ads": "0", "page_context": placement.page_context}
        selected = choose_creative(placement, context)
        self.assertIsNone(selected)


