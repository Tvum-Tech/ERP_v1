from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
import random


MOUNTING_STYLE_CHOICES = [
    'SURFACE',
    'RECESSED',
    'INGROUND',
    'TRACK MOUNTED',
]

def validate_mounting_styles(value):
    if not isinstance(value, list):
        raise ValidationError("compatible_mounting_styles must be a list")

    invalid = set(value) - set(MOUNTING_STYLE_CHOICES)
    if invalid:
        raise ValidationError(
            f"Invalid mounting styles: {', '.join(invalid)}. "
            f"Allowed values are: {', '.join(MOUNTING_STYLE_CHOICES)}"
        )


class Accessory(models.Model):
    
    accessory_name = models.CharField(max_length=100)
    accessory_type = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    compatible_mounting_styles = models.JSONField(
        default=list,
        validators=[validate_mounting_styles],
        help_text="Allowed values: SURFACE, RECESSED, INGROUND, TRACK MOUNTED"
    )

    min_diameter_mm = models.IntegerField(null=True, blank=True)
    max_diameter_mm = models.IntegerField(null=True, blank=True)
    compatible_ip_class = models.IntegerField(null=True, blank=True)

    accessory_category = models.CharField(
        max_length=50,
        choices=[
            ('MOUNTING', 'Mounting'),
            ('OPTICAL', 'Optical'),
            ('DECORATIVE', 'Decorative'),
            ('INSTALLATION', 'Installation'),
        ]
    )

    environment = models.CharField(
        max_length=20,
        choices=[('INDOOR', 'Indoor'), ('OUTDOOR', 'Outdoor')],
        default='INDOOR'
    )
    
    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    
    def __str__(self):
        return self.accessory_name