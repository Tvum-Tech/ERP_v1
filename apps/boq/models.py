from django.db import models
from apps.projects.models import Project, Area
from apps.masters.models import Product, Driver, Accessory
from django.contrib.auth import get_user_model


User = get_user_model()


class BOQ(models.Model):
    """
    BOQ (Bill of Quantities) Model with Configuration Version Tracking.
    
    ERP Rules:
    - Each BOQ is generated FROM a specific configuration version
    - BOQ stores source_configuration_version for reproducibility
    - BOQ versioning is separate from configuration versioning
    - Draft BOQ is editable, Final BOQ is locked
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("DRAFT", "Draft"),
            ("COMMERCIAL_APPROVED", "Commercial Approved"),
            ("FINAL", "Final"),
        ],
        default="DRAFT"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # ERP: Track which configuration version this BOQ was generated from
    source_configuration_version = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("project", "version")
        indexes = [
            models.Index(fields=['project', 'source_configuration_version']),
        ]


class BOQItem(models.Model):
    boq = models.ForeignKey(BOQ, on_delete=models.CASCADE, related_name="items")
    area = models.ForeignKey(
        Area,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="boq_items"
    )

    item_type = models.CharField(
        max_length=20,
        choices=[
            ("PRODUCT", "Product"),
            ("DRIVER", "Driver"),
            ("ACCESSORY", "Accessory"),
        ]
    )

    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.PROTECT)
    driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.PROTECT)
    accessory = models.ForeignKey(Accessory, null=True, blank=True, on_delete=models.PROTECT)
    parent_product = models.ForeignKey(
    Product,
    null=True,
    blank=True,
    on_delete=models.CASCADE,
    related_name="child_items"
)
    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    markup_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            # ✅ Existing correctness rule
            models.CheckConstraint(
                condition=(
                    models.Q(item_type="PRODUCT", product__isnull=False) |
                    models.Q(item_type="DRIVER", driver__isnull=False) |
                    models.Q(item_type="ACCESSORY", accessory__isnull=False)
                ),
                name="boq_item_type_reference_check"
            ),

            # 🔒 NEW: Prevent duplicate PRODUCT per area per BOQ
            models.UniqueConstraint(
                fields=["boq", "area", "product"],
                condition=models.Q(item_type="PRODUCT"),
                name="uniq_product_per_area_per_boq"
            ),
        ]
    

class AuditLogEntry(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    details = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Audit Log Entries"
