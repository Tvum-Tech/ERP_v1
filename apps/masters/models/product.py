from django.db import models
import random
from decimal import Decimal
from django.core.exceptions import ValidationError


class Product(models.Model):
    prod_id = models.AutoField(primary_key=True)
    make = models.CharField(max_length=100)
    order_code = models.CharField(max_length=100, null=True)

    luminaire_color_ral = models.CharField(max_length=100, null=True, blank=True)
    characteristics = models.TextField(null=True, blank=True)

    diameter_mm = models.IntegerField(null=True, blank=True)
    length_mm = models.IntegerField(null=True, blank=True)
    width_mm = models.IntegerField(null=True, blank=True)
    height_mm = models.IntegerField(null=True, blank=True)

    mounting_style = models.CharField(
        max_length=15,
        choices=[
            ('SURFACE', 'Surface Mounted'),
            ('RECESSED', 'Recessed'),
            ('INGROUND', 'Inground Mounted'),
            ('TRACK MOUNTED', 'Track Mounted'),
        ],
        default='SURFACE',
        null=True,
        blank=True
    )
    beam_angle_degree = models.CharField(max_length=100, blank=True, null=True)
    ip_class = models.IntegerField(null=True, blank=True)

    wattage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    op_voltage = models.IntegerField(null=True, blank=True)
    op_current = models.IntegerField(null=True, blank=True)

    lumen_output = models.IntegerField(null=True, blank=True)
    cct_kelvin = models.IntegerField(null=True, blank=True)
    cri_cci = models.IntegerField(null=True, blank=True)
    lumen_efficency = models.DecimalField(max_digits=5,decimal_places=2, null=True, blank=True)

    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    warranty_years = models.IntegerField(null=True, blank=True)

    website_link = models.URLField(null=True, blank=True)
    visual_image = models.ImageField(upload_to='lighting_specs/visual/', null=True, blank=True)
    illustrative_details = models.ImageField(upload_to='lighting_specs/illustrative/', null=True, blank=True)
    photometrics = models.ImageField(upload_to='lighting_specs/photometrics/', null=True, blank=True)


    base_price = models.DecimalField(
        max_digits= 10,
        decimal_places= 2,
        # default= Decimal("1.00")
        default=Decimal("0.00")
    )
    DRIVER_INTEGRATION_CHOICES = [
        ('INTEGRATED', 'Integrated Driver'),
        ('EXTERNAL', 'External Driver'),
    ]

    driver_integration = models.CharField(
        max_length=15,
        choices=DRIVER_INTEGRATION_CHOICES,
        default='EXTERNAL'
    )

    cutout_diameter_mm = models.IntegerField(null=True, blank=True)
    environment = models.CharField(
        max_length=20,
        choices=[('INDOOR', 'Indoor'), ('OUTDOOR', 'Outdoor')],
        default='INDOOR'
    )
    control_ready = models.CharField(
        max_length=20,
        choices=[('NONE', 'None'), ('DALI', 'DALI'), ('0-10V', '0-10V')],
        default='NONE'
    )
    electrical_type = models.CharField(
        max_length=2,
        choices=[('CC', 'Constant Current'), ('CV', 'Constant Voltage')],
        default='CC'
    )
    

    def clean(self):
        # Electrical validation
        if self.electrical_type == "CC" and not self.op_current:
            raise ValidationError(
                "CC product must define operating current (op_current)."
            )

        if self.electrical_type == "CV" and not self.op_voltage:
            raise ValidationError(
                "CV product must define operating voltage (op_voltage)."
            )


    def save(self, *args, **kwargs):
        self.full_clean()  # triggers clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.make} - {self.order_code}"
