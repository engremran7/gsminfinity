from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BrandDistributionView,
    DownloadLinkView,
    DownloadSessionStatusView,
    DriveBalanceReportView,
    FirmwareStorageLocationViewSet,
    InitiateFirmwareDownloadView,
    QuotaStatusView,
    ServiceAccountViewSet,
    SharedDriveAccountViewSet,
    UserDownloadSessionViewSet,
)

app_name = "storage"

router = DefaultRouter()
router.register("drives", SharedDriveAccountViewSet, basename="drives")
router.register("service-accounts", ServiceAccountViewSet, basename="service-accounts")
router.register(
    "storage-locations", FirmwareStorageLocationViewSet, basename="storage-locations"
)
router.register("my-downloads", UserDownloadSessionViewSet, basename="my-downloads")

urlpatterns = [
    # Download endpoints
    path(
        "download/initiate/",
        InitiateFirmwareDownloadView.as_view(),
        name="download-initiate",
    ),
    path(
        "download/session/<uuid:session_id>/",
        DownloadSessionStatusView.as_view(),
        name="download-session",
    ),
    path(
        "download/link/<uuid:session_id>/",
        DownloadLinkView.as_view(),
        name="download-link",
    ),
    # Quota & analytics
    path("quota/", QuotaStatusView.as_view(), name="quota-status"),
    # Admin endpoints
    path("admin/balance/", DriveBalanceReportView.as_view(), name="balance-report"),
    path(
        "admin/brand-distribution/",
        BrandDistributionView.as_view(),
        name="brand-distribution",
    ),
    # ViewSet routes
    path("", include(router.urls)),
]
