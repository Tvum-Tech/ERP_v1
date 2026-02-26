from django.db.models import Q
from apps.masters.models import Driver, Accessory
from apps.masters.models import ProductDriverMap, ProductAccessoryMap


# ============================================================
# DRIVER COMPATIBILITY (HYBRID ENGINE)
# ============================================================

def get_compatible_drivers(products):

    if not products.exists():
        return Driver.objects.none()

    # If any product has integrated driver → no external drivers
    if products.filter(driver_integration="INTEGRATED").exists():
        return Driver.objects.none()

    compatible_drivers = Driver.objects.all()

    for product in products:

        qs = compatible_drivers

        # Electrical type
        qs = qs.filter(constant_type=product.electrical_type)

        # Wattage
        if product.wattage:
            qs = qs.filter(max_wattage__gte=product.wattage)

        # CC validation
        if product.electrical_type == "CC":
            if not product.op_current:
                return Driver.objects.none()

            qs = qs.filter(
                output_current_min_ma__lte=product.op_current,
                output_current_max_ma__gte=product.op_current
            )

        # CV validation
        if product.electrical_type == "CV":
            if not product.op_voltage:
                return Driver.objects.none()

            qs = qs.filter(
                output_voltage_min__lte=product.op_voltage,
                output_voltage_max__gte=product.op_voltage
            )

        # IP
        if product.ip_class:
            qs = qs.filter(ip_class__gte=product.ip_class)

        # Environment
        qs = qs.filter(environment=product.environment)

        # Dimming
        if product.control_ready and product.control_ready != "NONE":
            qs = qs.filter(dimming_protocol=product.control_ready)

        compatible_drivers = qs

    # -------------------------
    # Mapping Override (Hybrid)
    # -------------------------

    for product in products:

        mapped_ids = ProductDriverMap.objects.filter(
            product=product
        ).values_list("driver_id", flat=True)

        if mapped_ids.exists():
            compatible_drivers = compatible_drivers.filter(
                id__in=mapped_ids
            )

    return compatible_drivers.distinct()


# ============================================================
# ACCESSORY COMPATIBILITY (HYBRID ENGINE)
# ============================================================

def get_compatible_accessories(products):

    if not products.exists():
        return Accessory.objects.none()

    compatible_accessories = Accessory.objects.all()

    for product in products:

        qs = compatible_accessories

        # Environment
        qs = qs.filter(environment=product.environment)

        # IP
        if product.ip_class:
            qs = qs.filter(
                Q(compatible_ip_class__isnull=True) |
                Q(compatible_ip_class__gte=product.ip_class)
            )

        # Diameter
        if getattr(product, "diameter_mm", None):
            qs = qs.filter(
                Q(min_diameter_mm__isnull=True) |
                Q(min_diameter_mm__lte=product.diameter_mm),
                Q(max_diameter_mm__isnull=True) |
                Q(max_diameter_mm__gte=product.diameter_mm)
            )

        # Mounting style (optimized)
        if getattr(product, "mounting_style", None):
            qs = qs.filter(
                compatible_mounting_styles__contains=[product.mounting_style]
            )

        compatible_accessories = qs

    # -------------------------
    # Mapping Override (Hybrid)
    # -------------------------

    for product in products:

        mapped_ids = ProductAccessoryMap.objects.filter(
            product=product
        ).values_list("accessory_id", flat=True)

        if mapped_ids.exists():
            compatible_accessories = compatible_accessories.filter(
                id__in=mapped_ids
            )

    return compatible_accessories.distinct()