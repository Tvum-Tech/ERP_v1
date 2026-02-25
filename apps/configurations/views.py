
from rest_framework import viewsets, status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from django.db import transaction
from apps.configurations.models import (
    LightingConfiguration,
    ConfigurationDriver,
    ConfigurationAccessory,
)

from apps.configurations.serializers import LightingConfigurationSerializer, ConfigurationAccessorySerializer,ConfigurationDriverSerializer
from apps.configurations.services.versioning import create_configuration_version
from apps.projects.models import Project, Area
from apps.masters.models import Product
from apps.common.permissions import IsEditorOrReadOnly
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import SubArea

class LightingConfigurationListAPI(ModelViewSet):
    queryset = LightingConfiguration.objects.all()
    serializer_class = LightingConfigurationSerializer

    def get_queryset(self):
        
        project_id = self.request.query_params.get("project_id")
        show_all = self.request.query_params.get("show_all")
        print(f"project_id: {project_id}")
        qs = LightingConfiguration.objects.all()

        if project_id:
            qs = qs.filter(project_id=project_id)
        print(show_all)
        # default → onlynon active
        # if show_all != "None":
        #     qs = qs.filter(is_active=True)

        return qs.select_related(
            "product",
            "area",
            "subarea"
        ).prefetch_related(
            "configuration_drivers__driver",
            "accessories__accessory"
        ).order_by("configuration_version")

    serializer_class = LightingConfigurationSerializer
    permission_classes = [IsEditorOrReadOnly]
    filter_backends = [SearchFilter, DjangoFilterBackend]

    @action(detail=False, methods=["get"], url_path="by-area/(?P<area_id>[^/.]+)")
    def by_area(self, request, area_id=None):
        configs = self.get_queryset().filter(area_id=area_id)
        serializer = self.get_serializer(configs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="by-subarea/(?P<subarea_id>[^/.]+)")
    def by_subarea(self, request, subarea_id=None):
        configs = self.get_queryset().filter(subarea_id=subarea_id)
        serializer = self.get_serializer(configs, many=True)
            
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="by-project/(?P<project_id>[^/.]+)"
    )
    def by_project(self, request, project_id=None):
        """
        Returns active configuration for project-level BOQ.
        Used when project.inquiry_type = PROJECT_LEVEL
        """
        print("BY PROJECT HIT", project_id)
        configs = self.get_queryset().filter(
            project_id=project_id
        )
        serializer = self.get_serializer(configs, many=True)
        return Response(serializer.data)


    def create(self, request, *args, **kwargs):
        area_id = request.data.get("area")
        product_id = request.data.get("product")

        if not area_id or not product_id:
            raise ValidationError("area and product are required")
        
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=204)
    
    @action(detail=False, methods=["post"], url_path="save_batch")


    def save_batch(self, request):
        data = request.data
        
        area_id = data.get("area_id")
        subarea_id = data.get("subarea_id")
        project_id = data.get("project_id")

        products = data.get("products", [])
        drivers = data.get("drivers", [])
        accessories = data.get("accessories", [])

        # -------------------------------
        # BASIC VALIDATION
        # -------------------------------
        if not products:
            return Response(
                {"error": "Products are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        project = None
        area = None
        subarea = None

        # -------------------------------
        # PRIORITY 1: SUBAREA PROVIDED
        # -------------------------------
        if subarea_id:
            try:
                subarea = SubArea.objects.select_related("area__project").get(id=subarea_id)
                area = subarea.area
                project = area.project
            except SubArea.DoesNotExist:
                return Response(
                    {"error": "Subarea not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        # -------------------------------
        # PRIORITY 2: AREA PROVIDED
        # -------------------------------
        elif area_id:
            try:
                area = Area.objects.select_related("project").get(id=area_id)
                project = area.project
            except Area.DoesNotExist:
                return Response(
                    {"error": "Area not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        # -------------------------------
        # PRIORITY 3: PROJECT-LEVEL CONFIG
        # -------------------------------
        elif project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return Response(
                    {"error": "Project not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            return Response(
                {"error": "project_id or area_id or subarea_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # -------------------------------
        # ERP RULE ENFORCEMENT
        # -------------------------------
        if project.inquiry_type == "AREA_WISE" and not area:
            return Response(
                {"error": "Area is required for area-wise projects"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Optional stricter rule:
        # If you want subarea mandatory for AREA_WISE:
        # if project.inquiry_type == "AREA_WISE" and not subarea:
        #     return Response({"error": "Subarea is required"}, status=400)

        # -------------------------------
        # CREATE CONFIGURATION VERSION
        # -------------------------------
        try:
            with transaction.atomic():

                result = create_configuration_version(
                    project_id=project.id,
                    area_id=area.id if area else None,
                    subarea_id=subarea.id if subarea else None,
                    products_data=products,
                    drivers_data=drivers,
                    accessories_data=accessories,
                )

                return Response(result, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {
                    "error": "Internal Server Error",
                    "details": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    @action(
        detail=False,
        methods=["post"],
        url_path="compatibility",
        permission_classes=[AllowAny]
    )
    def compatibility(self, request):
        """
        ERP-Grade Compatibility Endpoint
        
        POST /api/configurations/compatibility/
        
        Validates and returns only drivers and accessories compatible with ALL selected products.
        """
        print("COMPATIBILITY HIT", request.data)
        product_ids = request.data.get('product_ids', [])
        
        if not product_ids:
            return Response(
                {"error": "product_ids is required and must not be empty"}, 
                status=400
            )
        
        if not isinstance(product_ids, list):
            return Response(
                {"error": "product_ids must be a list"}, 
                status=400
            )

        try:
            products = Product.objects.filter(pk__in=product_ids)
            
            if not products.exists():
                return Response(
                    {"error": "No valid products found with provided IDs"}, 
                    status=400
                )
            
            if len(product_ids) != products.count():
                return Response(
                    {"error": "Some product IDs are invalid"}, 
                    status=400
                )
            
            from apps.masters.services.compatibility import (
                get_compatible_drivers,
                get_compatible_accessories
            )
            compatible_drivers = get_compatible_drivers(products)
            compatible_accessories = get_compatible_accessories(products)
            
            from apps.masters.serializers import (
                DriverCompatibilitySerializer,
                AccessoryCompatibilitySerializer
            )
            
            drivers_data = DriverCompatibilitySerializer(compatible_drivers, many=True).data
            accessories_data = AccessoryCompatibilitySerializer(compatible_accessories, many=True).data
            
            return Response({
                "drivers": drivers_data,
                "accessories": accessories_data,
                "meta": {
                    "product_count": products.count(),
                    "driver_count": len(drivers_data),
                    "accessory_count": len(accessories_data)
                }
            })

        except Exception as e:
            return Response(
                {"error": f"Compatibility check failed: {str(e)}"}, 
                status=400
            )

    @action(detail=False, methods=["get"], url_path="compatibility/product/(?P<product_id>[^/.]+)")
    def product_compatibility(self, request, product_id=None):
        """
        ERP-Grade Single Product Compatibility Endpoint
        """
        try:
            product = Product.objects.get(pk=product_id)
            
            from apps.masters.services.compatibility import (
                get_compatible_drivers,
                get_compatible_accessories
            )
            drivers = get_compatible_drivers(product)
            accessories = get_compatible_accessories(product)

            return Response({
                "product_id": product.id,
                "drivers": [
                    {
                        "id": d.id,
                        "driver_code": d.driver_code,
                        "driver_make": d.driver_make,
                        "driver_type": d.constant_type,
                        "max_wattage": d.max_wattage,
                    }
                    for d in drivers
                ],
                "accessories": [
                    {
                        "id": a.id,
                        "accessory_name": a.accessory_name,
                        "accessory_category": a.accessory_category,
                    }
                    for a in accessories
                ]
            })
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


class ConfigurationAccessoryViewSet(viewsets.ModelViewSet):
    queryset = ConfigurationAccessory.objects.all()
    serializer_class = ConfigurationAccessorySerializer
    permission_classes = [IsEditorOrReadOnly]
    filter_backends = [SearchFilter, DjangoFilterBackend]


class ConfigurationDriverViewSet(viewsets.ModelViewSet):
    queryset = ConfigurationDriver.objects.all()
    serializer_class = ConfigurationDriverSerializer
    permission_classes = [IsEditorOrReadOnly]
    filter_backends = [SearchFilter, DjangoFilterBackend]

    def create(self, request, *args, **kwargs):
        configuration_id = request.data.get("configuration")

        existing = ConfigurationDriver.objects.filter(
            configuration_id=configuration_id
        ).first()

        if existing:
            serializer = self.get_serializer(
                existing,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=200)

        return super().create(request, *args, **kwargs)