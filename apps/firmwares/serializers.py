from django.core.validators import MinLengthValidator
from rest_framework import serializers

from .models import (
    BrandCreationRequest,
    ModelCreationRequest,
    PendingFirmware,
    SchemaUpdateProposal,
    VariantCreationRequest,
)


class PendingFirmwareUploadSerializer(serializers.Serializer):
    brand_id = serializers.IntegerField(required=False, allow_null=True)
    model_id = serializers.IntegerField(required=False, allow_null=True)
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    is_password_protected = serializers.BooleanField()
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[MinLengthValidator(1)],
    )
    extra_info = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    file = serializers.FileField()


class PendingFirmwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = PendingFirmware
        fields = "__all__"


class SchemaUpdateProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemaUpdateProposal
        fields = "__all__"


class BrandCreationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandCreationRequest
        fields = "__all__"


class ModelCreationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelCreationRequest
        fields = "__all__"


class VariantCreationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = VariantCreationRequest
        fields = "__all__"
