from rest_framework import serializers
from .models import Project, Area, SubArea


class LocationMetadataSerializer(serializers.Serializer):
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)


class AreaDetailsSerializer(serializers.Serializer):
    UNIT_CHOICES = (
        ("sqft", "sqft"),
        ("sqmt", "sqmt"),
        ("acre", "acre"),
    )

    landscape_area = serializers.FloatField(required=False, min_value=0)
    interior_area = serializers.FloatField(required=False, min_value=0)
    facade_area = serializers.FloatField(required=False, min_value=0)
    unit = serializers.ChoiceField(choices=UNIT_CHOICES, required=False)


class SubAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubArea
        fields = [
            "id",
            "area",
            "name",
            "subarea_code",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["subarea_code", "created_at"]


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = '__all__'
        

from decimal import Decimal
from rest_framework import serializers
from .models import Project
# # from .nested_serializers import (
#     LocationMetadataSerializer,
#     AreaDetailsSerializer,
#     AreaSerializer,
# )


class ProjectSerializer(serializers.ModelSerializer):
    location_metadata = LocationMetadataSerializer(required=False)
    area_details = AreaDetailsSerializer(required=False)
    areas = AreaSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "client_name",
            "project_code",
            "inquiry_type",

            # ✅ Currency Fields
            "currency",
            "exchange_rate",
            "exchange_rate_locked",
            "exchange_rate_locked_at",

            "location_metadata",
            "status",
            "expected_completion_date",
            "refered_by",
            "segment_area",
            "expecetd_mhr",
            "fee",
            "area_details",
            "description",
            "notes",
            "tags",
            "created_at",
            "areas",
        ]

        read_only_fields = (
            "project_code",
            "created_at",
            "id",
        )

    # ---------------------------------------------------
    # Representation
    # ---------------------------------------------------
    def to_representation(self, instance):
        rep = super().to_representation(instance)

        rep.setdefault(
            "location_metadata",
            instance.location_metadata or {
                "address": "",
                "city": "",
                "state": "",
                "country": "",
            },
        )

        rep.setdefault(
            "area_details",
            instance.area_details or {
                "landscape_area": 0,
                "interior_area": 0,
                "facade_area": 0,
                "unit": "sqft",
            },
        )

        return rep

    # ---------------------------------------------------
    # Create
    # ---------------------------------------------------
    def create(self, validated_data):
        loc = validated_data.pop("location_metadata", None)
        area = validated_data.pop("area_details", None)

        if loc is not None:
            default_loc = {
                "address": "",
                "city": "",
                "state": "",
                "country": "",
            }
            default_loc.update(loc)
            validated_data["location_metadata"] = default_loc

        if area is not None:
            default_area = {
                "landscape_area": 0,
                "interior_area": 0,
                "facade_area": 0,
                "unit": "sqft",
            }
            default_area.update(area)
            validated_data["area_details"] = default_area

        return super().create(validated_data)

    # ---------------------------------------------------
    # Update
    # ---------------------------------------------------
    def update(self, instance, validated_data):
        loc = validated_data.pop("location_metadata", serializers.empty)
        area = validated_data.pop("area_details", serializers.empty)

        if loc is not serializers.empty:
            existing_loc = instance.location_metadata or {
                "address": "",
                "city": "",
                "state": "",
                "country": "",
            }
            existing_loc.update(loc)
            validated_data["location_metadata"] = existing_loc

        if area is not serializers.empty:
            existing_area = instance.area_details or {
                "landscape_area": 0,
                "interior_area": 0,
                "facade_area": 0,
                "unit": "sqft",
            }

            existing_area.update(area)

            # Prevent negative values
            for k, v in list(existing_area.items()):
                if k == "unit":
                    if not v:
                        existing_area[k] = "sqft"
                    continue

                try:
                    if v is None:
                        existing_area[k] = 0
                    elif float(v) < 0:
                        raise serializers.ValidationError(
                            {"area_details": "Values must be non-negative"}
                        )
                except (TypeError, ValueError):
                    raise serializers.ValidationError(
                        {"area_details": f"Invalid numeric value for {k}"}
                    )

            validated_data["area_details"] = existing_area

        return super().update(instance, validated_data)

    # ---------------------------------------------------
    # Currency Validation
    # ---------------------------------------------------
    def validate(self, attrs):
        currency = attrs.get(
            "currency",
            getattr(self.instance, "currency", "INR"),
        )

        rate = attrs.get(
            "exchange_rate",
            getattr(self.instance, "exchange_rate", 1),
        )

        if currency != "INR":
            if not rate or Decimal(rate) <= 0:
                raise serializers.ValidationError(
                    {"exchange_rate": "Valid exchange rate required for foreign currency"}
                )

        return attrs
