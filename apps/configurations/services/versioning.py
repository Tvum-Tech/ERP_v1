"""
Configuration Versioning Service
=================================
ERP-grade immutable configuration versioning.

Rules:
- Versions auto-increment per (project, area)
- Versions are append-only
- Only latest version is active
- BOQ references version snapshot
"""

from django.db import transaction
from django.db.models import Max
from django.core.exceptions import ValidationError

from apps.configurations.models import (
    LightingConfiguration,
    ConfigurationDriver,
    ConfigurationAccessory
)

from apps.masters.models import Product, Driver, Accessory


# ============================================================
# VERSION HELPERS
# ============================================================

def get_latest_configuration_version(project_id, area_id):
    latest = LightingConfiguration.objects.filter(
        project_id=project_id,
        area_id=area_id
    ).aggregate(max_version=Max("configuration_version"))["max_version"]

    return (latest or 0) + 1


def mark_previous_versions_inactive(project_id, area_id, new_version):
    LightingConfiguration.objects.filter(
        project_id=project_id,
        area_id=area_id
    ).exclude(
        configuration_version=new_version
    ).update(is_active=False)


# ============================================================
# CREATE NEW CONFIGURATION VERSION (ENTERPRISE SAFE)
# ============================================================

@transaction.atomic
def create_configuration_version(
    project_id,
    area_id,
    subarea_id,
    products_data
):
    """
    Create new immutable configuration version.

    products_data format:
    [
        {
            "product_id": 1,
            "quantity": 5,
            "drivers": [
                {"driver_id": 3, "quantity": 1}
            ],
            "accessories": [
                {"accessory_id": 2, "quantity": 1}
            ]
        }
    ]
    """

    if not products_data:
        raise ValidationError("At least one product is required.")

    # --------------------------------------------------
    # VALIDATE PRODUCTS
    # --------------------------------------------------

    product_ids = [p["product_id"] for p in products_data]

    existing_products = set(
        Product.objects.filter(prod_id__in=product_ids)
        .values_list("prod_id", flat=True)
    )

    missing_products = set(product_ids) - existing_products
    if missing_products:
        raise ValidationError(f"Invalid product IDs: {missing_products}")

    # --------------------------------------------------
    # VERSIONING
    # --------------------------------------------------

    next_version = get_latest_configuration_version(project_id, area_id)

    mark_previous_versions_inactive(
        project_id,
        area_id,
        next_version
    )

    created_configs = []

    # --------------------------------------------------
    # CREATE CONFIGURATIONS
    # --------------------------------------------------

    for prod_data in products_data:

        config = LightingConfiguration.objects.create(
            project_id=project_id,
            area_id=area_id,
            subarea_id=subarea_id,
            configuration_version=next_version,
            is_active=True,
            product_id=prod_data["product_id"],
            quantity=prod_data.get("quantity", 1),
        )

        created_configs.append(config)

        # --------------------------------------------------
        # DRIVER SNAPSHOT
        # --------------------------------------------------

        drivers_list = prod_data.get("drivers", [])

        if drivers_list:
            for driver_data in drivers_list:

                driver_id = driver_data.get("driver_id")

                if not Driver.objects.filter(id=driver_id).exists():
                    raise ValidationError(
                        f"Invalid driver ID: {driver_id}"
                    )

                ConfigurationDriver.objects.create(
                    configuration=config,
                    driver_id=driver_id,
                    quantity=driver_data.get("quantity", 1),
                )

        else:
            # Auto assign default driver if required
            config.assign_default_driver()

        # --------------------------------------------------
        # ACCESSORY SNAPSHOT
        # --------------------------------------------------

        accessories_list = prod_data.get("accessories", [])

        for acc_data in accessories_list:

            acc_id = acc_data.get("accessory_id")

            if not Accessory.objects.filter(id=acc_id).exists():
                raise ValidationError(
                    f"Invalid accessory ID: {acc_id}"
                )

            ConfigurationAccessory.objects.create(
                configuration=config,
                accessory_id=acc_id,
                quantity=acc_data.get("quantity", 1),
            )

    return {
        "version": next_version,
        "configuration_count": len(created_configs),
        "project_id": project_id,
        "area_id": area_id,
    }


# ============================================================
# GET ACTIVE VERSION
# ============================================================

def get_active_configuration_version(project_id, area_id):

    return LightingConfiguration.objects.filter(
        project_id=project_id,
        area_id=area_id,
        is_active=True
    ).values_list("configuration_version", flat=True).first()


# ============================================================
# SNAPSHOT FETCH (FOR BOQ)
# ============================================================

def get_configuration_snapshot(project_id, area_id, configuration_version):

    configurations = LightingConfiguration.objects.filter(
        project_id=project_id,
        area_id=area_id,
        configuration_version=configuration_version
    ).select_related("product")

    config_ids = list(configurations.values_list("id", flat=True))

    drivers = ConfigurationDriver.objects.filter(
        configuration_id__in=config_ids
    ).select_related("driver")

    accessories = ConfigurationAccessory.objects.filter(
        configuration_id__in=config_ids
    ).select_related("accessory")

    return {
        "configurations": configurations,
        "drivers": drivers,
        "accessories": accessories,
        "version": configuration_version,
    }


# ============================================================
# DELETE PROTECTION
# ============================================================

def delete_configuration_version_prohibited():
    raise Exception(
        "Configuration versions cannot be deleted. "
        "ERP systems maintain immutable audit trails."
    )