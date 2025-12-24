from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FirmwareUploadView,
    PendingFirmwareViewSet,
    ModerationView,
    SchemaUpdateProposalViewSet,
    BrandCreationRequestViewSet,
    ModelCreationRequestViewSet,
    VariantCreationRequestViewSet,
)
from .autofill_views import (
    autofill_brand,
    autofill_model,
    autofill_variant,
)
from .public_views import (
    firmware_browse,
    brand_list,
    brand_detail,
    model_detail,
    firmware_detail,
    firmware_download,
    firmware_download_start,
    api_firmware_stats,
    api_search_autocomplete,
)

app_name = "firmwares"

router = DefaultRouter()
router.register("pending", PendingFirmwareViewSet, basename="pending-firmware")
router.register("schema-proposals", SchemaUpdateProposalViewSet, basename="schema-proposals")
router.register("brand-requests", BrandCreationRequestViewSet, basename="brand-requests")
router.register("model-requests", ModelCreationRequestViewSet, basename="model-requests")
router.register("variant-requests", VariantCreationRequestViewSet, basename="variant-requests")

urlpatterns = [
    # Public browsing pages
    path("", firmware_browse, name="browse"),
    path("brands/", brand_list, name="brand_list"),
    path("brand/<slug:slug>/", brand_detail, name="brand_detail"),
    path("brand/<slug:brand_slug>/<slug:model_slug>/", model_detail, name="model_detail"),
    
    # Firmware detail and download
    path("<str:firmware_type>/<uuid:firmware_id>/", firmware_detail, name="firmware_detail"),
    path("<str:firmware_type>/<uuid:firmware_id>/download/", firmware_download, name="firmware_download"),
    path("<str:firmware_type>/<uuid:firmware_id>/download/start/", firmware_download_start, name="firmware_download_start"),
    
    # API endpoints
    path("api/<str:firmware_type>/<uuid:firmware_id>/stats/", api_firmware_stats, name="api_firmware_stats"),
    path("api/search/autocomplete/", api_search_autocomplete, name="api_search_autocomplete"),
    
    # Admin/upload endpoints
    path("upload/", FirmwareUploadView.as_view(), name="firmware-upload"),
    path("moderate/<uuid:pk>/", ModerationView.as_view(), name="firmware-moderate"),

    # Auto-fill endpoints
    path("brand/<int:brand_id>/autofill/", autofill_brand, name="autofill-brand"),
    path("model/<int:model_id>/autofill/", autofill_model, name="autofill-model"),
    path("variant/<int:variant_id>/autofill/", autofill_variant, name="autofill-variant"),

    path("api/", include(router.urls)),
]
