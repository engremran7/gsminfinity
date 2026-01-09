import logging

from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import (
    FirmwareStorageLocation,
    ServiceAccount,
    SharedDriveAccount,
    UserDownloadSession,
)
from .serializers import (
    FirmwareStorageLocationSerializer,
    InitiateDownloadSerializer,
    QuotaStatusSerializer,
    ServiceAccountSerializer,
    SharedDriveAccountSerializer,
    UserDownloadSessionSerializer,
)
from .services import ServiceAccountRouter
from .services.orchestrator import DownloadOrchestrator
from .services.placement import SmartPlacementAlgorithm

logger = logging.getLogger(__name__)


class InitiateFirmwareDownloadView(views.APIView):
    """
    POST /api/storage/download/initiate/
    Start firmware download process - copies to user's GDrive
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InitiateDownloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        firmware_type = serializer.validated_data['firmware_type']
        firmware_id = serializer.validated_data['firmware_id']

        # Get firmware model
        from apps.firmware import models as firmware_models

        model_map = {
            'official': firmware_models.OfficialFirmware,
            'engineering': firmware_models.EngineeringFirmware,
            'readback': firmware_models.ReadbackFirmware,
            'modified': firmware_models.ModifiedFirmware,
            'other': firmware_models.OtherFirmware,
            'unclassified': firmware_models.UnclassifiedFirmware
        }

        model_class = model_map.get(firmware_type)
        if not model_class:
            return Response(
                {'error': f'Invalid firmware type: {firmware_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        firmware = get_object_or_404(model_class, id=firmware_id)
        content_type = ContentType.objects.get_for_model(model_class)

        orchestrator = DownloadOrchestrator()

        try:
            session = orchestrator.initiate_download(
                user=request.user,
                firmware_object=firmware,
                content_type=content_type
            )

            return Response(
                UserDownloadSessionSerializer(session).data,
                status=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Download initiation failed: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DownloadSessionStatusView(views.APIView):
    """
    GET /api/storage/download/session/{session_id}/
    Check download session status
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(
            UserDownloadSession,
            id=session_id,
            user=request.user
        )
        return Response(UserDownloadSessionSerializer(session).data)


class DownloadLinkView(views.APIView):
    """
    GET /api/storage/download/link/{session_id}/
    Get final download link (marks session as downloading)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        from django.utils import timezone

        session = get_object_or_404(
            UserDownloadSession,
            id=session_id,
            user=request.user
        )

        if session.status != 'ready':
            return Response(
                {
                    'error': f'Download not ready. Current status: {session.status}',
                    'status': session.status
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if session.is_expired():
            return Response(
                {'error': 'Download link has expired'},
                status=status.HTTP_410_GONE
            )

        # Track download start
        if not session.download_started_at:
            session.download_started_at = timezone.now()
            session.status = 'downloading'
            session.save(update_fields=['download_started_at', 'status'])

        return Response({
            'download_link': session.user_gdrive_link,
            'expires_at': session.expires_at,
            'time_remaining_seconds': int(session.time_remaining().total_seconds()),
            'file_name': session.storage_location.file_name if session.storage_location else None,
            'file_size': session.storage_location.file_size_bytes if session.storage_location else None
        })


class QuotaStatusView(views.APIView):
    """
    GET /api/storage/quota/
    Get current quota status across all shared drives and service accounts
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        router = ServiceAccountRouter()
        distribution = router.get_shared_drive_distribution()

        serializer = QuotaStatusSerializer(distribution, many=True)

        total_available_gb = sum(d['available_quota_gb'] for d in distribution)
        total_quota_gb = sum(d['total_quota_gb'] for d in distribution)

        return Response({
            'shared_drives': serializer.data,
            'total_available_gb': round(total_available_gb, 2),
            'total_quota_gb': total_quota_gb,
            'utilization_percent': round((total_quota_gb - total_available_gb) / total_quota_gb * 100, 2) if total_quota_gb > 0 else 0
        })


class DriveBalanceReportView(views.APIView):
    """
    GET /api/storage/admin/balance/
    Get drive balance analysis (admin only)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        placement = SmartPlacementAlgorithm()
        analysis = placement.balance_drives()
        return Response(analysis)


class BrandDistributionView(views.APIView):
    """
    GET /api/storage/admin/brand-distribution/
    Get brand distribution across drives (admin only)
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        placement = SmartPlacementAlgorithm()
        distribution = placement.get_brand_distribution()
        return Response(distribution)


# ViewSets for admin management

class SharedDriveAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin API for viewing shared drive accounts
    """
    permission_classes = [IsAdminUser]
    queryset = SharedDriveAccount.objects.all().order_by('-priority', 'name')
    serializer_class = SharedDriveAccountSerializer

    @action(detail=True, methods=['post'])
    def update_health(self, request, pk=None):
        """Manually trigger health status update"""
        drive = self.get_object()
        drive.update_health_status()
        return Response({
            'health_status': drive.health_status,
            'utilization_percent': drive.utilization_percent()
        })


class ServiceAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin API for viewing service accounts
    """
    permission_classes = [IsAdminUser]
    queryset = ServiceAccount.objects.select_related('shared_drive').all()
    serializer_class = ServiceAccountSerializer
    filterset_fields = ['shared_drive', 'is_active', 'is_banned']

    @action(detail=True, methods=['post'])
    def reset_quota(self, request, pk=None):
        """Manually reset service account quota"""
        sa = self.get_object()
        sa.used_quota_today_gb = 0.0
        sa.consecutive_failures = 0
        sa.save()
        return Response(ServiceAccountSerializer(sa).data)


class FirmwareStorageLocationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API for viewing firmware storage locations
    """
    permission_classes = [IsAuthenticated]
    queryset = FirmwareStorageLocation.objects.all()
    serializer_class = FirmwareStorageLocationSerializer
    filterset_fields = ['storage_type', 'is_primary', 'is_verified']


class UserDownloadSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User's download session history
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserDownloadSessionSerializer

    def get_queryset(self):
        return UserDownloadSession.objects.filter(
            user=self.request.user
        ).select_related('storage_location').order_by('-created_at')

    @action(detail=True, methods=['delete'])
    def cancel(self, request, pk=None):
        """Cancel a pending/copying download session"""
        session = self.get_object()

        if session.status not in ['pending', 'copying']:
            return Response(
                {'error': 'Can only cancel pending or copying sessions'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.status = 'expired'
        session.save()

        return Response({'status': 'cancelled'})
