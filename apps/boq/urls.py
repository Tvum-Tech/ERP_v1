from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GenerateBOQAPI,
    BOQSummaryAPI,
    BOQSummaryDetailAPI,
    BOQVersionsListAPI,
    BOQApproveAPI,
    BOQExportPDFAPI,
    BOQExportExcelAPI,
    ApplyMarginAPI,
    BOQItemPriceUpdateAPI,
    BOQItemViewSet
)

router = DefaultRouter()
router.register("items", BOQItemViewSet, basename="boq-items")

urlpatterns = [
    path('', include(router.urls)),
    path('generate/<int:project_id>/', GenerateBOQAPI.as_view()),
    path('summary/<int:project_id>/', BOQSummaryAPI.as_view()),
    path('summary/detail/<int:boq_id>/', BOQSummaryDetailAPI.as_view()),
    path('versions/<int:project_id>/', BOQVersionsListAPI.as_view()), # Mandatory Endpoint
    path('approve/<int:boq_id>/', BOQApproveAPI.as_view()),
    
    # Download PDF/EXCEL
    path("export/pdf/<int:boq_id>/", BOQExportPDFAPI.as_view()),
    path("export/excel/<int:boq_id>/", BOQExportExcelAPI.as_view()),
    path("apply-margin/<int:boq_id>/", ApplyMarginAPI.as_view()),
    
    # Price Override (Transactional)
    path("items/<int:boq_item_id>/price/", BOQItemPriceUpdateAPI.as_view()),
    path("items/<int:boq_item_id>/", BOQItemViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update"})),
]
