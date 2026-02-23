"""
Integration test for ERP Configuration Versioning System
Tests the complete workflow:
1. save_batch creates first version (v1)
2. save_batch again increments version (v2)
3. Previous versions marked inactive
4. BOQ uses specific version snapshot
5. Cannot delete configuration versions
"""

from django.test import TestCase
from django.db import IntegrityError
from django.db.models import ProtectedError
from decimal import Decimal

from apps.projects.models import Project, Area
from apps.masters.models import Product, Driver, Accessory
from apps.configurations.models import LightingConfiguration, ConfigurationDriver, ConfigurationAccessory
from apps.boq.models import BOQ
from apps.configurations.services.versioning import (
    create_configuration_version,
    get_latest_configuration_version,
    get_active_configuration_version,
)
from apps.boq.services.boq_service import generate_boq


class ConfigurationVersioningTestCase(TestCase):
    """Test ERP-grade configuration versioning"""

    def setUp(self):
        """Create test data"""
        from decimal import Decimal
        
        self.project = Project.objects.create(
            name="Office Complex A",
            status="ACTIVE",
            fee=Decimal("10000.00")
        )
        
        self.area1 = Area.objects.create(
            project=self.project,
            name="Conference Room 1",
            area_type="CONFERENCE",
            area_code="CONF1"
        )
        
        self.area2 = Area.objects.create(
            project=self.project,
            name="Meeting Room 2",
            area_type="MEETING",
            area_code="MEET2"
        )
        
        # Create test products
        self.product1 = Product.objects.create(
            order_code="PHIL-DL-10W",
            make="Philips",
            model="DL-10W-R",
            base_price=Decimal("500.00")
        )
        
        self.product2 = Product.objects.create(
            order_code="OSRAM-DL-15W",
            make="Osram",
            model="DL-15W-CW",
            base_price=Decimal("600.00")
        )
        
        # Create test driver
        self.driver = Driver.objects.create(
            driver_code="MW-CC-350",
            make="Meanwell",
            base_price=Decimal("200.00")
        )
        
        # Create test accessory
        self.accessory = Accessory.objects.create(
            accessory_code="CLIP-KIT",
            accessory_name="Spring Clip Kit",
            base_price=Decimal("50.00")
        )

    def test_versioning_increment_on_save_batch(self):
        """Test that save_batch creates v1, then v2, etc."""
        
        # Create v1
        result_v1 = create_configuration_version(
            project_id=self.project.id,
            area_id=self.area1.id,
            products_data=[{
                'product_id': self.product1.id,
                'quantity': 5,
            }],
            drivers_data=[{
                'driver_id': self.driver.id,
                'quantity': 5,
            }],
            accessories_data=[{
                'accessory_id': self.accessory.id,
                'quantity': 10,
            }]
        )
        
        self.assertEqual(result_v1['version'], 1)
        self.assertEqual(result_v1['products_created'], 1)
        self.assertEqual(result_v1['drivers_created'], 1)
        self.assertEqual(result_v1['accessories_created'], 1)
        
        # Verify v1 is marked active
        v1_config = LightingConfiguration.objects.get(
            area=self.area1,
            configuration_version=1
        )
        self.assertTrue(v1_config.is_active)
        
        # Create v2
        result_v2 = create_configuration_version(
            project_id=self.project.id,
            area_id=self.area1.id,
            products_data=[{
                'product_id': self.product2.id,
                'quantity': 10,
            }],
            drivers_data=[{
                'driver_id': self.driver.id,
                'quantity': 10,
            }],
            accessories_data=[{
                'accessory_id': self.accessory.id,
                'quantity': 20,
            }]
        )
        
        self.assertEqual(result_v2['version'], 2)
        
        # Verify v1 is now inactive
        v1_config.refresh_from_db()
        self.assertFalse(v1_config.is_active)
        
        # Verify v2 is active
        v2_config = LightingConfiguration.objects.get(
            area=self.area1,
            configuration_version=2
        )
        self.assertTrue(v2_config.is_active)

    def test_unique_constraint_on_version_tuple(self):
        """Test that (project, area, version) must be unique"""
        
        # Create v1
        create_configuration_version(
            project_id=self.project.id,
            area_id=self.area1.id,
            products_data=[{
                'product_id': self.product1.id,
                'quantity': 5,
            }],
            drivers_data=[],
            accessories_data=[]
        )
        
        # Try to create duplicate v1 in same area - should fail
        with self.assertRaises(IntegrityError):
            LightingConfiguration.objects.create(
                project=self.project,
                area=self.area1,
                subarea=None,
                product=self.product1,
                quantity=5,
                configuration_version=1
            )

    def test_boq_uses_active_configuration_version(self):
        """Test that BOQ generation uses only active configurations"""
        
        # Create v1
        create_configuration_version(
            project_id=self.project.id,
            area_id=self.area1.id,
            products_data=[{
                'product_id': self.product1.id,
                'quantity': 5,
            }],
            drivers_data=[],
            accessories_data=[]
        )
        
        # Create v2 (will mark v1 inactive)
        create_configuration_version(
            project_id=self.project.id,
            area_id=self.area1.id,
            products_data=[{
                'product_id': self.product2.id,
                'quantity': 10,
            }],
            drivers_data=[],
            accessories_data=[]
        )
        
        # Generate BOQ
        boq = generate_boq(self.project)
        
        # BOQ should use v2 (the active version)
        self.assertEqual(boq.source_configuration_version, 2)
        
        # BOQ should only contain product2 (from v2)
        from apps.boq.models import BOQItem
        product_items = BOQItem.objects.filter(
            boq=boq,
            item_type='PRODUCT'
        )
        self.assertEqual(product_items.count(), 1)
        self.assertEqual(product_items.first().product.id, self.product2.id)

    def test_deletion_prevented(self):
        """Test that deleting configuration versions is prevented"""
        
        # Create v1
        result = create_configuration_version(
            project_id=self.project.id,
            area_id=self.area1.id,
            products_data=[{
                'product_id': self.product1.id,
                'quantity': 5,
            }],
            drivers_data=[],
            accessories_data=[]
        )
        
        # Get the configuration
        config = LightingConfiguration.objects.get(id=result['product_configs'][0]['id'])
        
        # Try to delete - should raise ProtectedError
        with self.assertRaises(ProtectedError) as context:
            config.delete()
        
        self.assertIn("ERP audit compliance", str(context.exception))

    def test_get_latest_version_number(self):
        """Test getting the latest version number for an (project, area)"""
        
        # Initially should be 1
        version = get_latest_configuration_version(self.project.id, self.area1.id)
        self.assertEqual(version, 1)
        
        # Create v1
        create_configuration_version(
            project_id=self.project.id,
            area_id=self.area1.id,
            products_data=[{
                'product_id': self.product1.id,
                'quantity': 5,
            }],
            drivers_data=[],
            accessories_data=[]
        )
        
        # Now should be 2
        version = get_latest_configuration_version(self.project.id, self.area1.id)
        self.assertEqual(version, 2)

    def test_different_areas_have_independent_versions(self):
        """Test that each area has independent version numbering"""
        
        # Create v1 in area1
        create_configuration_version(
            project_id=self.project.id,
            area_id=self.area1.id,
            products_data=[{
                'product_id': self.product1.id,
                'quantity': 5,
            }],
            drivers_data=[],
            accessories_data=[]
        )
        
        # Create v1 in area2 (should work, different area)
        result = create_configuration_version(
            project_id=self.project.id,
            area_id=self.area2.id,
            products_data=[{
                'product_id': self.product2.id,
                'quantity': 10,
            }],
            drivers_data=[],
            accessories_data=[]
        )
        
        self.assertEqual(result['version'], 1)  # v1 for area2
        
        # Now create v2 in area1
        result = create_configuration_version(
            project_id=self.project.id,
            area_id=self.area1.id,
            products_data=[{
                'product_id': self.product2.id,
                'quantity': 10,
            }],
            drivers_data=[],
            accessories_data=[]
        )
        
        self.assertEqual(result['version'], 2)  # v2 for area1


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3'}},
        )
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['__main__'])
