"""
Compatibility Service Layer
===========================
Centralized ERP-grade compatibility logic for Lighting BOQ system.

Rules:
- No database writes
- Pure filtering functions
- Deterministic and reusable
- Accepts Product QuerySet, returns Driver/Accessory QuerySet
"""

from django.db.models import Q
from apps.masters.models import Driver, Accessory


def get_compatible_drivers(products):
    """
    Returns QuerySet of drivers compatible with ALL given products.
    
    Args:
        products: QuerySet of Product objects
        
    Returns:
        QuerySet of Driver objects (intersection of all compatible drivers)
        
    Compatibility Rules (ALL must match):
    1. product.driver_integration == 'EXTERNAL'
    2. driver.constant_type == product.electrical_type
    3. driver.max_wattage >= product.wattage
    4. Voltage/Current ranges overlap:
       - CC: driver.output_current_ma == product.op_current
       - CV: driver voltage range covers product voltage
    5. driver.ip_class >= product.ip_class (if defined)
    6. If product is control-ready, driver must support that protocol
    """
    
    if not products.exists():
        return Driver.objects.none()
    
    # If ANY product has INTEGRATED driver, return empty set
    if products.filter(driver_integration='INTEGRATED').exists():
        return Driver.objects.none()
    
    # Start with all drivers as candidates
    compatible_drivers = None
    
    for product in products:
        # Build filters for this product
        product_filters = Q()
        
        # Rule 1: Already checked via INTEGRATED check above
        # All products must be EXTERNAL at this point
        
        # Rule 2: Constant type must match electrical_type
        if product.electrical_type:
            product_filters &= Q(constant_type=product.electrical_type)
        
        # Rule 3: Wattage compatibility
        total_wattage = sum(p.wattage or 0 for p in products)

        if total_wattage:
            product_filters &= Q(max_wattage__gte=total_wattage)
        
        # Rule 4: Voltage/Current compatibility
        if product.electrical_type == 'CC':
            # Constant Current: exact current match required
            if product.op_current:
                product_filters &= Q(output_current_ma=product.op_current)
        elif product.electrical_type == 'CV':
            # Constant Voltage: voltage range must cover product voltage
            if product.op_voltage:
                product_filters &= Q(
                    output_voltage_min__lte=product.op_voltage,
                    output_voltage_max__gte=product.op_voltage
                )
        
        # Rule 5: IP class compatibility
        if product.ip_class and isinstance(product.ip_class, int):
            product_filters &= Q(ip_class__gte=product.ip_class)
        
        # Rule 6: Control/Dimming protocol compatibility
        if product.control_ready and product.control_ready != 'NONE':
            # Driver must support the same dimming protocol
            product_filters &= Q(
                dimming_protocols__contains=[product.control_ready]
            )
        
        # Get compatible drivers for this product
        product_compatible = Driver.objects.filter(product_filters)
        
        # Intersect with previous results
        if compatible_drivers is None:
            compatible_drivers = product_compatible
        else:
            # Intersection: only drivers compatible with ALL products
            current_pks = set(
                compatible_drivers.values_list("pk", flat=True)
            )
            new_pks = set(
                product_compatible.values_list("pk", flat=True)
            )
            intersect_pks = current_pks & new_pks
            compatible_drivers = Driver.objects.filter(pk__in=intersect_pks)
    
    return compatible_drivers if compatible_drivers is not None else Driver.objects.none()


def get_compatible_accessories(products):
    """
    Returns QuerySet of accessories compatible with ALL given products.
    
    Args:
        products: QuerySet of Product objects
        
    Returns:
        QuerySet of Accessory objects (intersection of all compatible accessories)
        
    Compatibility Rules (ALL must match):
    1. Product mounting style ∈ accessory.compatible_mounting_styles
    2. If diameter exists: min_diameter <= product.diameter <= max_diameter
    3. If IP exists: accessory.ip_class >= product.ip_class
    4. Environment compatibility (Indoor/Outdoor)
    
    NOTE: Rule 1 uses Python-level filtering instead of ORM __contains
    to ensure SQLite compatibility (SQLite doesn't support JSONField__contains).
    """
    
    if not products.exists():
        return Accessory.objects.none()
    
    compatible_accessories = None
    
    for product in products:
        product_filters = Q()
        
        # Rule 2: Diameter compatibility
        if product.diameter_mm:
            product_filters &= Q(
                min_diameter_mm__lte=product.diameter_mm,
                max_diameter_mm__gte=product.diameter_mm
            )
        
        # Rule 3: IP class compatibility
        if product.ip_class:
            product_filters &= Q(compatible_ip_class__gte=product.ip_class)
        
        # Rule 4: Environment compatibility
        # This assumes there's an 'environment' field on Accessory model
        # If it doesn't exist, this can be removed or handled differently
        # if product.environment:
        #     product_filters &= Q(compatible_environment=product.environment)
        
        # Get accessories matching non-mounting criteria (all rules except Rule 1)
        product_compatible = Accessory.objects.filter(product_filters)
        
        # Rule 1: Mounting style compatibility (Python-level filtering for SQLite compatibility)
        # Load all candidates and filter by checking if product.mounting_style exists
        # in accessory.compatible_mounting_styles JSONField array
        if product.mounting_style:
            # Filter in Python: only include accessories where product.mounting_style
            # is in the compatible_mounting_styles list
            filtered_accessories = []
            for accessory in product_compatible:
                # Get the compatible_mounting_styles field (JSONField as list)
                compat_styles = accessory.compatible_mounting_styles or []

                # Ensure it's a list (defensive check)
                if isinstance(compat_styles, list):
                    if product.mounting_style in compat_styles:
                        filtered_accessories.append(accessory.pk)
                elif isinstance(compat_styles, str):
                    # Handle case where it might be a single string
                    if product.mounting_style == compat_styles:
                        filtered_accessories.append(accessory.pk)
            
            # Convert filtered list to QuerySet using pk__in
            product_compatible = Accessory.objects.filter(pk__in=filtered_accessories)
        
        # Intersect with previous results
        if compatible_accessories is None:
            compatible_accessories = product_compatible
        else:
            # Intersection: only accessories compatible with ALL products
            # Convert to lists of PKs and intersect
            current_pks = set(compatible_accessories.values_list('pk', flat=True))
            new_pks = set(product_compatible.values_list('pk', flat=True))
            intersect_pks = current_pks & new_pks
            
            # Return QuerySet of intersected PKs
            compatible_accessories = Accessory.objects.filter(pk__in=intersect_pks)
    
    return compatible_accessories if compatible_accessories is not None else Accessory.objects.none()