"""
Configuration Versioning Service
=================================
Implements ERP-grade configuration versioning with immutable snapshots.

Key Concepts:
- Versions auto-increment per (project, area)
- Each version is immutable (append-only)
- Only latest version is active
- BOQ references specific version for reproducibility
"""

from django.db import transaction
from django.db.models import Max, Q
from apps.configurations.models import LightingConfiguration, ConfigurationAccessory, ConfigurationDriver
from apps.masters.models import Product, Driver, Accessory
from apps.configurations.models import (
    LightingConfiguration,
    ConfigurationDriver,
    ConfigurationAccessory
)

def get_latest_configuration_version(project_id, area_id):
    """
    Get the latest configuration version number for a given (project, area).
    
    Returns:
        int: Latest version number (1 if none exists)
    """
    latest = LightingConfiguration.objects.filter(
        project_id=project_id,
        area_id=area_id
    ).aggregate(max_version=Max('configuration_version'))['max_version']
    
    return (latest or 0) + 1


def mark_previous_versions_inactive(project_id, area_id, new_version):
    """
    Mark all previous configuration versions as inactive.
    Only the latest version should have is_active=True.
    
    Args:
        project_id: Project ID
        area_id: Area ID
        new_version: The new version number being activated
    """
    LightingConfiguration.objects.filter(
        project_id=project_id,
        area_id=area_id
    ).exclude(
        configuration_version=new_version
    ).update(is_active=False)


@transaction.atomic
def create_configuration_version(project_id, area_id, products_data, drivers_data, accessories_data):
    print("products_data",products_data)
    """
    Create a new IMMUTABLE configuration version.

    ERP GUARANTEE:
    ✅ Append-only versioning
    ✅ No updates to past versions
    ✅ Drivers and accessories saved correctly
    """

    # -------------------------------
    # VALIDATION
    # -------------------------------
    if not products_data:
        raise ValidationError("At least one product is required")

    # Validate products
    product_ids = [p.get("product_id") for p in products_data]
    existing_products = set(
        Product.objects.filter(prod_id__in=product_ids)
        .values_list("prod_id", flat=True)
    )
    missing_products = set(product_ids) - existing_products
    if missing_products:
        raise ValidationError(f"Invalid product IDs: {missing_products}")

    # Validate drivers
    if drivers_data:
        driver_ids = [d.get("driver_id") for d in drivers_data]
        existing_drivers = set(
            Driver.objects.filter(id__in=driver_ids)
            .values_list("id", flat=True)
        )
        missing_drivers = set(driver_ids) - existing_drivers
        if missing_drivers:
            raise ValidationError(f"Invalid driver IDs: {missing_drivers}")

    # Validate accessories
    if accessories_data:
        acc_ids = [a.get("accessory_id") for a in accessories_data]
        existing_accessories = set(
            Accessory.objects.filter(id__in=acc_ids)
            .values_list("id", flat=True)
        )
        missing_acc = set(acc_ids) - existing_accessories
        if missing_acc:
            raise ValidationError(f"Invalid accessory IDs: {missing_acc}")

    # -------------------------------
    # VERSIONING
    # -------------------------------
    next_version = get_latest_configuration_version(project_id, area_id)

    # Deactivate previous versions
    mark_previous_versions_inactive(project_id, area_id, next_version)

    # -------------------------------
    # CREATE PRODUCT CONFIGS
    # -------------------------------
    created_configs = []

    for prod_data in products_data:
        config = LightingConfiguration.objects.create(
            project_id=project_id,
            area_id=area_id,
            configuration_version=next_version,
            is_active=True,
            product_id=prod_data["product_id"],
            quantity=prod_data.get("quantity", 1),
        )
        created_configs.append(config)

        # -------------------------------
        # DRIVER LINK (per product)
        # -------------------------------
        drivers_data = prod_data.get("drivers",[])
        for driver in drivers_data:
            driver_id = driver.get("driver_id")
            if driver_id:
                ConfigurationDriver.objects.create(
                    configuration=config,
                    driver_id=driver_id,
                    quantity=driver.get("quantity", 1),
            )

        # -------------------------------
        # ACCESSORY LINKS (per product)
        # -------------------------------
        accessories = prod_data.get("accessories", [])
        for acc in accessories:
            ConfigurationAccessory.objects.create(
                configuration=config,
                accessory_id=acc.get("accessory_id"),
                quantity=acc.get("quantity", 1),
            )

    # -------------------------------
    # RESPONSE
    # -------------------------------
    return {
        "version": next_version,
        "configuration_count": len(created_configs),
        "area_id": area_id,
        "project_id": project_id,
    }

def get_active_configuration_version(project_id, area_id):
    """
    Get the active (latest) configuration version for a given (project, area).
    
    Returns:
        int: Active version number or None if no configurations exist
    """
    result = LightingConfiguration.objects.filter(
        project_id=project_id,
        area_id=area_id,
        is_active=True
    ).values_list('configuration_version', flat=True).first()
    
    return result


def get_configuration_snapshot(project_id, area_id, configuration_version):
    """
    Retrieve the complete configuration snapshot for a specific version.
    This is used by BOQ generation to ensure reproducibility.
    
    Returns:
        dict: {
            'configurations': [LightingConfiguration objects],
            'drivers': [ConfigurationDriver objects],
            'accessories': [ConfigurationAccessory objects]
        }
    """
    configurations = LightingConfiguration.objects.filter(
        project_id=project_id,
        area_id=area_id,
        configuration_version=configuration_version
    ).select_related('product')
    
    # Collect drivers from configurations
    config_ids = list(configurations.values_list('id', flat=True))
    drivers = ConfigurationDriver.objects.filter(
        configuration_id__in=config_ids
    ).select_related('driver')
    
    # Collect accessories (from first config only, as per model design)
    accessories = ConfigurationAccessory.objects.filter(
        configuration_id__in=config_ids
    ).select_related('accessory')
    
    return {
        'configurations': configurations,
        'drivers': drivers,
        'accessories': accessories,
        'version': configuration_version
    }


def delete_configuration_version_prohibited():
    """
    This function intentionally raises an error.
    Configuration versions must NEVER be deleted (ERP audit compliance).
    """
    raise Exception(
        "Configuration versions cannot be deleted. "
        "ERP systems maintain immutable audit trails. "
        "You can only create new versions."
    )
