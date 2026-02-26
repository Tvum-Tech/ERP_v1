from django.db import models
from django.db.models import ProtectedError
from django.core.exceptions import ValidationError

from apps.projects.models import Area, Project, SubArea
from apps.masters.models.product import Product
from apps.masters.models.driver import Driver
from apps.masters.models.accessory import Accessory
from apps.masters.models import ProductDriverMap


# ============================================================
# MAIN CONFIGURATION MODEL (Product Selection Layer)
# ============================================================

class LightingConfiguration(models.Model):

    # --------------------------------------------------------
    # CORE FIELDS
    # --------------------------------------------------------

    project = models.ForeignKey(Project, on_delete=models.CASCADE)

    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configurations"
    )

    subarea = models.ForeignKey(
        SubArea,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configurations"
    )

    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    # ERP Versioning
    configuration_version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def clean(self):

        # ================================
        # 1️⃣ PROJECT STRUCTURE VALIDATION
        # ================================

        if self.project.inquiry_type == "PROJECT_LEVEL":
            if self.area or self.subarea:
                raise ValidationError(
                    "Area/SubArea must be empty for PROJECT_LEVEL projects."
                )

        if self.project.inquiry_type == "AREA_WISE":
            if self.subarea and not self.area:
                raise ValidationError(
                    "SubArea cannot exist without Area."
                )

            if self.subarea and self.subarea.area != self.area:
                raise ValidationError(
                    "SubArea must belong to the selected Area."
                )

        # ================================
        # 2️⃣ PRODUCT + QUANTITY VALIDATION
        # ================================

        if not self.product:
            raise ValidationError("Product is required.")

        if not self.quantity or self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

    # --------------------------------------------------------
    # AUTO DEFAULT DRIVER ASSIGNMENT
    # --------------------------------------------------------

    def assign_default_driver(self):
        """
        Auto-assign default compatible driver if:
        - Product requires EXTERNAL driver
        - No driver assigned yet
        """

        from apps.configurations.services.compatibility import get_compatible_drivers

        if self.product.driver_integration != "EXTERNAL":
            return

        if self.configuration_drivers.exists():
            return

        compatible_drivers = get_compatible_drivers(
            type(self.product).objects.filter(pk=self.product.pk)
        )

        default_map = ProductDriverMap.objects.filter(
            product=self.product,
            is_default=True
        ).first()

        if default_map and default_map.driver in compatible_drivers:

            ConfigurationDriver.objects.create(
                configuration=self,
                driver=default_map.driver,
                quantity=1
            )
        else:
            raise ValidationError(
                "No compatible default driver available for this product."
            )

    # --------------------------------------------------------
    # SAVE OVERRIDE
    # --------------------------------------------------------

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # --------------------------------------------------------
    # META
    # --------------------------------------------------------

    class Meta:
        unique_together = [
            ('project', 'area', 'subarea', 'configuration_version', 'product')
        ]

        indexes = [
            models.Index(fields=['project', 'area', 'is_active']),
            models.Index(fields=['project', 'area', 'configuration_version']),
        ]

    # --------------------------------------------------------
    # STRING REPRESENTATION
    # --------------------------------------------------------

    def __str__(self):
        area_name = self.area.name if self.area else "Project-Level"
        product_code = self.product.order_code if self.product else "Unknown"
        return f"{area_name} - {product_code} (v{self.configuration_version})"

    # --------------------------------------------------------
    # PREVENT DELETE (ERP RULE)
    # --------------------------------------------------------

    def delete(self, *args, **kwargs):
        raise ProtectedError(
            "Configuration versions cannot be deleted (ERP audit compliance). "
            "Create a new version instead.",
            self
        )


# ============================================================
# DRIVER SNAPSHOT MODEL
# ============================================================

class ConfigurationDriver(models.Model):
    """
    Immutable driver records linked to configuration versions.
    """

    configuration = models.ForeignKey(
        LightingConfiguration,
        on_delete=models.CASCADE,
        related_name="configuration_drivers"
    )

    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def clean(self):
        from apps.configurations.compatibility import get_compatible_drivers

        product = self.configuration.product

        if product.driver_integration == "INTEGRATED":
            raise ValidationError(
                "Integrated product cannot have external driver."
            )

        compatible_drivers = get_compatible_drivers(
            type(product).objects.filter(pk=product.pk)
        )

        if self.driver not in compatible_drivers:
            raise ValidationError(
                f"Driver '{self.driver}' is not compatible "
                f"with product '{product}'."
            )

        if not self.quantity or self.quantity <= 0:
            raise ValidationError("Driver quantity must be greater than zero.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# ============================================================
# ACCESSORY SNAPSHOT MODEL
# ============================================================

class ConfigurationAccessory(models.Model):
    """
    Immutable accessory records linked to configuration versions.
    """

    configuration = models.ForeignKey(
        LightingConfiguration,
        on_delete=models.CASCADE,
        related_name="accessories"
    )

    accessory = models.ForeignKey(Accessory, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def clean(self):
        from apps.configurations.compatibility import get_compatible_accessories

        compatible_accessories = get_compatible_accessories(
            type(self.configuration.product).objects.filter(
                pk=self.configuration.product.pk
            )
        )

        if self.accessory not in compatible_accessories:
            raise ValidationError(
                f"Accessory '{self.accessory}' is not compatible "
                f"with product '{self.configuration.product}'."
            )

        if not self.quantity or self.quantity <= 0:
            raise ValidationError("Accessory quantity must be greater than zero.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)