from rest_framework import mixins, viewsets
from apps.masters.models.product import Product
from apps.masters.models.driver import Driver
from apps.masters.models.accessory import Accessory
from .serializers import (
    ProductSerializer,
    DriverSerializer,
    AccessorySerializer)
from apps.common.permissions import IsAdminOrReadOnly
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser

class ProductListAPI(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('-prod_id')
    serializer_class = ProductSerializer
    lookup_field = "prod_id"   # IMPORTANT: use prod_id for lookups instead of default pk/id
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["make", "order_code", "wattage", "lumen_output", "cct_kelvin", "beam_angle_degree"]
    
    def create(self, request, *args, **kwargs):
        print("MASTER CREATE HIT:", request.data)
        print("AUTH HEADER:", request.headers.get('Authorization'))
        print("CSRF HEADER:", request.headers.get('X-CSRFToken'))
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("❌ VALIDATION FAILED:", serializer.errors)
        return super().create(request, *args, **kwargs)
    
    def list(self, request, *args, **kwargs):
        print("DEBUG: Master Product List Hit")
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            q = request.GET.get('q', '')
            products = self.queryset.filter(make__icontains=q) | self.queryset.filter(order_code__icontains=q)
            from django.shortcuts import render
            return render(request, 'includes/product_list_partial.html', {'products': products})
        return super().list(request, *args, **kwargs)
    
class DriverListAPI(viewsets.ModelViewSet):
    queryset = Driver.objects.all().order_by('-id')
    serializer_class = DriverSerializer
    permission_classes = [IsAdminOrReadOnly]

    # FIX: add this
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["driver_make", "driver_code", "constant_type"]

    # ----------------------------
    # CREATE DRIVER (ADMIN)
    # ----------------------------
    def create(self, request, *args, **kwargs):
        print("MASTER CREATE HIT (Driver):", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("❌ VALIDATION FAILED (Driver):", serializer.errors)
        return super().create(request, *args, **kwargs)

    # ----------------------------
    # LIST DRIVERS (MASTER LIST / SEARCH)
    # ----------------------------
    def list(self, request, *args, **kwargs):
        print("DEBUG: Master Driver List Hit")

        # AJAX search (used in admin / master screens)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            q = request.GET.get("q", "")
            drivers = (
                self.queryset.filter(driver_make__icontains=q)
                | self.queryset.filter(driver_code__icontains=q)
            )
            from django.shortcuts import render
            return render(
                request,
                "includes/driver_list_partial.html",
                {"drivers": drivers},
            )

        return super().list(request, *args, **kwargs)

    # ----------------------------
    # ERP: COMPATIBLE DRIVERS
    # ----------------------------
    @action(detail=False, methods=["get"])
    def compatible(self, request):
        product_id = request.query_params.get("product")

        if not product_id:
            return Response([])

        try:
            product = Product.objects.get(prod_id=product_id)
        except Product.DoesNotExist:
            return Response([])

        if not product.electrical_type or not product.wattage:
            return Response([])

        drivers = Driver.objects.filter(
            constant_type__isnull=False,
            max_wattage__isnull=False,
            constant_type=product.electrical_type,
            max_wattage__gte=product.wattage
        )

        serializer = self.get_serializer(drivers, many=True)
        return Response(serializer.data)
    
class AccessoryListAPI(viewsets.ModelViewSet):
    queryset = Accessory.objects.all().order_by('-id')
    serializer_class = AccessorySerializer
    permission_classes = [IsAdminOrReadOnly]

    # FIX: add this
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["accessory_name", "accessory_type"]

    def create(self, request, *args, **kwargs):
        print("MASTER CREATE HIT (Accessory):", request.data)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("❌ VALIDATION FAILED (Accessory):", serializer.errors)
        return super().create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        print("DEBUG: Master Accessory List Hit")
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            q = request.GET.get('q', '')
            accessories = self.queryset.filter(accessory_name__icontains=q) | self.queryset.filter(accessory_type__icontains=q)
            from django.shortcuts import render
            return render(request, 'includes/accessory_list_partial.html', {'accessories': accessories})
        return super().list(request, *args, **kwargs)
    
    @action(detail=False, methods=["get"])
    def compatible(self, request):
        product_id = request.query_params.get("product")

        if not product_id:
            return Response([])

        try:
            product = Product.objects.get(prod_id=product_id)
        except Product.DoesNotExist:
            return Response([])

        # For now return all accessories
        accessories = Accessory.objects.all()

        serializer = self.get_serializer(accessories, many=True)
        return Response(serializer.data)


class ProductFilterAPIView(APIView):
    def post(self, request):
        filters = request.data

        qs = Product.objects.all()

        if filters.get("mounting_style"):
            qs = qs.filter(mounting_style=filters["mounting_style"])

        if filters.get("beam_angle_degree"):
            qs = qs.filter(
                beam_angle_degree__gte=filters["beam_angle_degree"][0],
                beam_angle_degree__lte=filters["beam_angle_degree"][1]
            )

        if filters.get("lumen_output"):
            qs = qs.filter(
                lumen_output__gte=filters["lumen_output"][0],
                lumen_output__lte=filters["lumen_output"][1]
            )

        if filters.get("cct_kelvin"):
            qs = qs.filter(cct_kelvin__in=filters["cct_kelvin"])

        if filters.get("wattage"):
            qs = qs.filter(wattage__lte=filters["wattage"])

        if filters.get("make"):
            qs = qs.filter(make__in=filters["make"])

        if filters.get("order_code"):
            qs = qs.filter(order_code__icontains=filters["order_code"])

        serializer = ProductSerializer(qs, many=True)
        return Response(serializer.data)