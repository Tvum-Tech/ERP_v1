from rest_framework import serializers
from apps.masters.models import Product, Driver, Accessory
from decimal import Decimal, InvalidOperation


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

    def validate(self, data):
        print(f"✅ VALIDATING [Product]: {data.get('make')} | Order Code: {data.get('order_code')}")
        return data

    def create(self, validated_data):
        print("SERIALIZER DATA:", validated_data)
        return super().create(validated_data)


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'

    def validate(self, data):
        print(f"✅ VALIDATING [Driver]: {data.get('driver_make')} | Code: {data.get('driver_code')}")
        return data

    def create(self, validated_data):
        print("SERIALIZER DATA:", validated_data)
        return super().create(validated_data)


class AccessorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = '__all__'

    def validate(self, data):
        print(f"✅ VALIDATING [Accessory]: {data.get('accessory_name')} | Type: {data.get('accessory_type')}")
        return data

    def create(self, validated_data):
        print("SERIALIZER DATA:", validated_data)
        return super().create(validated_data)
        
        
class ProductSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            'prod_id',
            'make',
            'order_code',
            'wattage',
            'lumen_output',
        )
        
class DriverSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = [
            "id",
            "driver_code",
            "driver_make",
            "constant_type",
            "dimming_protocol",
            "output_current_ma",
            "output_voltage_min",
            "output_voltage_max",
            "max_wattage",
            "ip_class",
            "dimmable",
            "base_price",
        ]
        
class AccessorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = [
            "id",
            "accessory_name",
            "accessory_type"
        ]


# ============================================
# COMPATIBILITY SERIALIZERS (ERP-Grade)
# ============================================

class DriverCompatibilitySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for driver compatibility responses.
    Contains only fields needed for selection and technical validation.
    """
    class Meta:
        model = Driver
        fields = [
            'id',
            'driver_code',
            'driver_make',
            'constant_type',
            'max_wattage',
            'output_current_ma',
            'output_voltage_min',
            'output_voltage_max',
            'dimming_protocol',
            'ip_class',
            'base_price',
        ]


class AccessoryCompatibilitySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for accessory compatibility responses.
    Contains only fields needed for selection and technical validation.
    """
    class Meta:
        model = Accessory
        fields = [
            'id',
            'accessory_name',
            'accessory_category',
            'accessory_type',
            'compatible_mounting_styles',
            'min_diameter_mm',
            'max_diameter_mm',
            'compatible_ip_class',
            'base_price',
        ]