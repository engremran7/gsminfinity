from django.shortcuts import get_object_or_404
from rest_framework import status, views, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.core.throttling import APIRateThrottle, UploadRateThrottle

from .models import (
    Brand,
    BrandCreationRequest,
    Model,
    ModelCreationRequest,
    PendingFirmware,
    SchemaUpdateProposal,
    Variant,
    VariantCreationRequest,
)
from .serializers import (
    BrandCreationRequestSerializer,
    ModelCreationRequestSerializer,
    PendingFirmwareSerializer,
    PendingFirmwareUploadSerializer,
    SchemaUpdateProposalSerializer,
    VariantCreationRequestSerializer,
)
from .services import (
    attempt_extraction,
    handle_upload,
    moderate_and_route,
    run_ai_analysis,
)


class FirmwareUploadView(views.APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UploadRateThrottle]

    def post(self, request):
        ser = PendingFirmwareUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        brand = (
            Brand.objects.filter(id=data.get("brand_id")).first()
            if data.get("brand_id")
            else None
        )
        model = (
            Model.objects.filter(id=data.get("model_id")).first()
            if data.get("model_id")
            else None
        )
        variant = (
            Variant.objects.filter(id=data.get("variant_id")).first()
            if data.get("variant_id")
            else None
        )
        try:
            pf = handle_upload(
                uploader=request.user,
                uploaded_brand=brand,
                uploaded_model=model,
                uploaded_variant=variant,
                file_obj=data["file"],
                is_password_protected=data["is_password_protected"],
                password=data.get("password"),
                extra_info=data.get("extra_info"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        attempt_extraction(pf)
        run_ai_analysis(pf)
        return Response(
            PendingFirmwareSerializer(pf).data, status=status.HTTP_201_CREATED
        )


class PendingFirmwareViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdminUser]
    throttle_classes = [APIRateThrottle]
    queryset = PendingFirmware.objects.all().order_by("-created_at")
    serializer_class = PendingFirmwareSerializer


class ModerationView(views.APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk: str):
        pf = get_object_or_404(PendingFirmware, pk=pk)
        decision = request.data.get("decision")
        category = request.data.get("category")
        subtype = request.data.get("subtype")
        brand_id = request.data.get("brand_id")
        model_id = request.data.get("model_id")
        variant_id = request.data.get("variant_id")
        notes = request.data.get("notes", "")
        unclassified_reason = request.data.get("unclassified_reason", "")
        brand = Brand.objects.filter(id=brand_id).first() if brand_id else None
        model = Model.objects.filter(id=model_id).first() if model_id else None
        variant = Variant.objects.filter(id=variant_id).first() if variant_id else None
        rec = moderate_and_route(
            pf,
            decision,
            admin_user=request.user,
            category=category,
            subtype=subtype,
            brand=brand,
            model=model,
            variant=variant,
            notes=notes,
            unclassified_reason=unclassified_reason,
        )
        return Response({"result": rec.id if rec else None, "decision": decision})


class SchemaUpdateProposalViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    queryset = SchemaUpdateProposal.objects.all().order_by("-created_at")
    serializer_class = SchemaUpdateProposalSerializer


class BrandCreationRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = BrandCreationRequest.objects.all().order_by("-created_at")
    serializer_class = BrandCreationRequestSerializer


class ModelCreationRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ModelCreationRequest.objects.all().order_by("-created_at")
    serializer_class = ModelCreationRequestSerializer


class VariantCreationRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = VariantCreationRequest.objects.all().order_by("-created_at")
    serializer_class = VariantCreationRequestSerializer
