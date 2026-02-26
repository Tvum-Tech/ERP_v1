from decimal import Decimal

from django.db import models
import random

class Driver(models.Model):
    driver_code = models.CharField(max_length=100, unique=True)
    driver_make = models.CharField(max_length=100)
    # driver_type = models.CharField(max_length=50)
    

    input_voltage_min = models.IntegerField(null=True, blank=True)
    input_voltage_max = models.IntegerField(null=True, blank=True)
    max_wattage = models.IntegerField(null=True, blank=True)

    dimmable = models.CharField(
        max_length=3,
        choices=[('YES', 'Yes'), ('NO', 'No')],
        default='YES'
    )

    output_current_min_ma = models.IntegerField(null=True, blank=True)
    output_current_max_ma = models.IntegerField(null=True, blank=True)
    output_voltage_min = models.IntegerField(null=True, blank=True)
    output_voltage_max = models.IntegerField(null=True, blank=True)

    constant_type = models.CharField(
        max_length=20,
        choices=[('CC', 'Constant Current'), ('CV', 'Constant Voltage')],
        default='CC'
    )
    dimming_protocol = models.CharField(
        max_length=20,
        choices=[
            ('NONE', 'Non Dimmable'),
            ('DALI', 'DALI'),
            ('0-10V', '0-10V'),
            ('1-10V', '1-10V'),
            ('TRIAC', 'TRIAC')
        ],
        default='NONE'
    )

    ip_class = models.IntegerField(null=True, blank=True)
    warranty_years = models.IntegerField(null=True, blank=True)

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
        return f"{self.driver_make} - {self.driver_code}"