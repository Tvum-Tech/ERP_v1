from django.db import models
from django.core.validators import MaxLengthValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils.timezone import now

def default_location_metadata():
    return {
        "address": "",
        "city": "",
        "state": "",
        "country": "",
    }

def default_area_details():
    return {
        "landscape_area": 0,
        "landscape_area_unit": "sq.ft",
        "interior_area": 0,
        "interior_area_unit": "sq.ft",
        "facade_area": 0,
        "facade_area_unit": "sq.ft",
    }
        
# Create your models here.
class Project(models.Model):
    
    # DEFAULT_BILLING_DETAILS = {
    #     "billing_type": "",
    #     "currency": "INR",
    #     "gst_percentage": 0,
    # }
    STATUS_CHOICES = [
        ('INQUIRY', 'Inquiry'),
        ("ACTIVE", "Active"),
        ("COMPLETED", "Completed"),
        ("ON_HOLD", "On Hold"),
    ]
    segement_choice = [
        ('MASTER PLANNING', 'Master Planning'),
        ('COMMERCIAL', 'Commercial'),
        ('PRIVATE RESIDENCE', 'Private Residence'),
        ('RESIDENTIAL TOWNSHIP', 'Residential Township'),
        ('LANDSCAPE', 'Landscape'),
        ('FACADE', 'Facade'),
        ('HOSPITALITY', 'Hospitality'),
        ('HEALTH CARE', 'Health Care'),
        ('PUBLIC SPACE', 'Public Space'),
        ('SEZ', 'Sez'),
        ('SPECIAL/OTHERS', 'Special/Others'),
        ('INDUSTRIAL', 'Industrial'),
        ('RETAIL', 'Retail'),
        ('INFRASTRUCTURE', 'Infrastructure'),
        ('INSTITUTIONS', 'Instituions'),
        ('MEMORIALS', 'Memorials'),
        ('MALL/MULTIPLEX', 'Mall/Multiplex'),
        ('CLUB HOUSE', 'Club House'),
        ('TEMPLE/GURUDWARA/CHURCH', 'Temple/Gurudwara/Church'),
    ]

    INQUIRY_TYPE_CHOICES = [
        ("AREA_WISE", "Inquiry with Areas & SubAreas"),
        ("PROJECT_LEVEL", "Inquiry at Project Level"),
    ]

    inquiry_type = models.CharField(
        max_length=20,
        choices=INQUIRY_TYPE_CHOICES,
        default='AREA_WISE',
        help_text="Defines inquiry structure: area-wise or project-level"
    )

    allow_project_only_boq = models.BooleanField(
        default=False,
        help_text="Derived from inquiry_type, not user-editable later"
    )
    
    name = models.CharField(max_length=150)

    project_code = models.CharField(max_length=50, unique=True)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # First save to get ID
        super().save(*args, **kwargs)

        # Generate project_code only once
        if is_new and not self.project_code:
            base_name = slugify(self.name or "project")[:10].upper()
            yymmdd = now().strftime("%Y%m%d")

            self.project_code = f"{base_name}-{self.pk}-{yymmdd}"

            # Save only project_code (no infinite loop)
            super().save(update_fields=["project_code"])
    
    client_name = models.CharField(max_length=150)
    # location = models.CharField(max_length=150, blank=True, null=True)
    '''
        Added the metadata in JSON format
        location, city, state, country
        fields can be added as json format
    '''
    location_metadata = models.JSONField(
        default=default_location_metadata,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="INQUIRY"
    )
    expected_completion_date = models.DateField(blank=True, null=True)
    refered_by = models.CharField(blank=True, null=True)
    segment_area = models.CharField(
        max_length=100,
        choices=segement_choice,
        default="MASTER PLANNING",
    )
    expecetd_mhr = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MaxValueValidator(100000)]
    )
    fee = models.PositiveIntegerField(
        validators=[MaxValueValidator(9999999999)]
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # billing_details = models.JSONField(default=dict, blank=True, null=True)
    area_details = models.JSONField(
        default=default_area_details,
        blank=True,
    )

    CURRENCY_CHOICES = [
        ("INR", "Indian Rupee"),
        ("USD", "US Dollar"),
        ("GBP", "British Pound"),
        ("THB", "Thai Baht"),
        ("AED", "UAE Dirham"),
        ("CNY", "Chinese Yuan"),
    ]

    currency = models.CharField(
        max_length=5,
        choices=CURRENCY_CHOICES,
        default="INR"
    )

    exchange_rate = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=1
    )

    exchange_rate_locked = models.BooleanField(default=False)
    exchange_rate_locked_at = models.DateTimeField(null=True, blank=True)


    notes = models.TextField(blank=True, null=True, max_length=1000)
    tags = models.TextField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name


# apps/projects/models.py
class Area(models.Model):
    project = models.ForeignKey(
        "Project",
        on_delete=models.CASCADE,
        related_name="areas"
    )

    name = models.CharField(max_length=100)

    area_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "name")
        ordering = ["id"]

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # First save to get ID
        super().save(*args, **kwargs)

        # Generate area_code only once
        if is_new and not self.area_code:
            base_name = slugify(self.name or "area")[:10].upper()
            yymmdd = now().strftime("%Y%m%d")

            self.area_code = f"{base_name}-{self.pk}-{yymmdd}"

            super().save(update_fields=["area_code"])

    def __str__(self):
        return f"{self.project.project_code} → {self.area_code}"


class SubArea(models.Model):
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name="subareas"
    )

    name = models.CharField(max_length=100)

    subarea_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("area", "name")
        ordering = ["id"]

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # First save to get ID
        super().save(*args, **kwargs)

        # Generate subarea_code only once
        if is_new and not self.subarea_code:
            base_name = slugify(self.name or "subarea")[:10].upper()
            yymmdd = now().strftime("%Y%m%d")

            self.subarea_code = f"{base_name}-{self.pk}-{yymmdd}"

            super().save(update_fields=["subarea_code"])

    def __str__(self):
        return f"{self.area.area_code} → {self.subarea_code}"