from django.db import models
from django.db.models import ProtectedError
from apps.projects.models import Area, Project, SubArea
from apps.masters.models.product import Product
from apps.masters.models.driver import Driver
from apps.masters.models.accessory import Accessory
# from django.utils import timezone, DateTimeField

# created_at = models.DateTimeField(auto_now_add=True)
# updated_at = models.DateTimeField(auto_now=True)

# Create your models here.
class LightingConfiguration(models.Model):
    def clean(self):
        from django.core.exceptions import ValidationError
        # PROJECT LEVEL MODE
        if self.project.inquiry_type == "PROJECT_LEVEL":
            if self.area or self.subarea:
                raise ValidationError(
                    "Area/SubArea must be empty for PROJECT_LEVEL projects."
                )

        # AREA WISE MODE
        if self.project.inquiry_type == "AREA_WISE":
            if self.subarea and not self.area:
                raise ValidationError(
                    "SubArea cannot exist without Area."
                )
            if self.subarea and self.subarea.area != self.area:
                raise ValidationError(
                    "SubArea must belong to the selected Area."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
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
    
    # ERP Versioning Fields
    configuration_version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    
    # Audit tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # Ensure (project, area, subarea, configuration_version, product) is unique
        unique_together = [
    ('project', 'area', 'subarea', 'configuration_version', 'product')
]        # Index for efficient querying of active versions
        indexes = [
            models.Index(fields=['project', 'area', 'is_active']),
            models.Index(fields=['project', 'area', 'configuration_version']),
        ]
        # Database-level constraints removed: cannot reference joined fields like project__inquiry_type.
        # Business rule is enforced at the model level in clean().
    
    def __str__(self):
        area_name = self.area.name if self.area else "Project-Level"
        product_code = (
            self.product.order_code
            if hasattr(self, "product") and self.product
            else "Unknown Product"
        )
        return f"{area_name} - {product_code} (v{self.configuration_version})"
    
    def delete(self, *args, **kwargs):
        """
        Prevent deletion of configuration versions.
        ERP systems maintain immutable audit trails.
        To deactivate a version, create a new version instead.
        """
        raise ProtectedError(
            "Configuration versions cannot be deleted (ERP audit compliance). "
            "Create a new version instead.",
            self
        )


class ConfigurationAccessory(models.Model):
    """
    Immutable accessory records linked to configuration versions.
    Each version stores complete snapshot of selected accessories.
    """
    configuration = models.ForeignKey(
        LightingConfiguration,
        on_delete=models.CASCADE,
        related_name='accessories'
    )
    accessory = models.ForeignKey(Accessory, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    
    # Audit tracking
    created_at = models.DateTimeField(auto_now_add=True)


class ConfigurationDriver(models.Model):
    """
    Immutable driver records linked to configuration versions.
    Each version stores complete snapshot of selected drivers.
    """
    configuration = models.ForeignKey(
        LightingConfiguration,
        on_delete=models.CASCADE,
        related_name="configuration_drivers"
    )
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    
    # Audit tracking
    created_at = models.DateTimeField(auto_now_add=True)