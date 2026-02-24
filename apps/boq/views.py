
from django.shortcuts import get_object_or_404
from apps.projects.models import Project
from apps.boq.models import BOQ, BOQItem
from django.utils import timezone
from apps.boq.services.boq_service import (
    get_project_boq_summary,
    get_boq_summary,
    generate_boq,
    approve_boq,
    apply_margin_to_boq
)
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from apps.boq.services.boq_service import BOQPDFBuilder
from apps.boq.services.boq_service import BOQExcelBuilder
from apps.boq.serializers import BOQSerializer, BOQItemSerializer, BOQItemWriteSerializer
from apps.common.authentication import QueryParamJWTAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.serializers import Serializer
# from django.http import HttpResponse
# from reportlab.pdfgen import canvas
# import openpyxl
# from openpyxl.workbook import Workbook
from django.core.exceptions import ValidationError
from apps.common.permissions import (
    IsAdmin, 
    IsEditor, 
    IsFinance, 
    IsEditorOrReadOnly
)
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend


class GenerateBOQAPI(APIView):
    # serializer_class = Serializer
    serializer_class = BOQSerializer
    permission_classes = [IsEditor]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    def post(self, request, project_id):
        try:
            project = get_object_or_404(Project, id=project_id)
            boq = generate_boq(project, request.user)

            from apps.boq.models import AuditLogEntry
            AuditLogEntry.objects.create(
                user=request.user,
                action="BOQ_GENERATED",
                details={"boq_id": boq.id, "version": boq.version}
            )

            return Response({
                "success": True,
                "details": BOQSerializer(boq).data
            })

        except Project.DoesNotExist:
            return Response(
                {"detail": "Project not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        except ValidationError as e:
            return Response(
                {"detail": e.message},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            print("erroe",e)
            import traceback
            traceback.print_exc()
            return Response(
                {"detail": f"Generation Error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class BOQSummaryAPI(APIView):
    """
    Project-wise BOQ summary (latest BOQ)
    """
    filter_backends = [SearchFilter, DjangoFilterBackend]
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        summary = get_project_boq_summary(project)
        if summary is None:
            return Response({"detail": "No BOQ found for project."}, status=status.HTTP_404_NOT_FOUND)
        boq = BOQ.objects.filter(project=project).order_by("-version").first()
        subtotal = sum([v["amount"] for v in summary["summary"].values()])
        margin_percent = getattr(boq, "margin_percent", 0)
        margin_amount = subtotal * (margin_percent / 100)
        grand_total = subtotal + margin_amount
        summary.update({
            "subtotal": subtotal,
            "margin_percent": margin_percent,
            "margin_amount": margin_amount,
            "grand_total": grand_total
        })
        return Response(summary)

class BOQSummaryDetailAPI(APIView):
    """
    Specific BOQ summary by ID (CUMULATIVE)
    """

    def get(self, request, boq_id):
        boq = get_object_or_404(BOQ, id=boq_id)
        print("params", request.query_params)
        # 🔥 cumulative BOQ items
        items = BOQItem.objects.filter(
            boq__project=boq.project,
            boq__version__lte=boq.version
        ).select_related(
            "product",
            "driver",
            "accessory",
            "area"
        ).order_by("boq__version", "id")

        # serialize items
        items_data = BOQItemSerializer(items, many=True).data

        # -------- summary calculation ----------
        summary_map = {}
        for item in items:
            key = item.item_type

            if key not in summary_map:
                summary_map[key] = {"quantity": 0, "amount": 0}

            summary_map[key]["quantity"] += item.quantity
            summary_map[key]["amount"] += float(item.final_price or 0)

        subtotal = sum(v["amount"] for v in summary_map.values())
        margin_percent = getattr(boq, "margin_percent", 0)
        margin_amount = subtotal * (margin_percent / 100)
        grand_total = subtotal + margin_amount

        return Response({
            "project_id": boq.project.id,
            "boq_id": boq.id,
            "version": boq.version,
            "status": boq.status,
            "created_at": boq.created_at,
            "source_configuration_version": boq.source_configuration_version,

            # cumulative totals
            "summary": summary_map,
            "subtotal": subtotal,
            "margin_percent": margin_percent,
            "margin_amount": margin_amount,
            "grand_total": grand_total,

            # 🔥 NEW FIELD
            "items": items_data
        })


class BOQVersionsListAPI(APIView):
    """
    List all BOQ versions for a project.
    MANDATORY ENDPOINT CHECK.
    """
    filter_backends = [SearchFilter, DjangoFilterBackend]
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        boqs = list(
            BOQ.objects.filter(project=project)
            .order_by('-version')
            .values(
                'id',
                'version',
                'status',
                'created_at',
                'source_configuration_version'
            )
        )
        return Response(boqs)


  
class BOQApproveAPI(APIView):
    serializer_class = serializers.Serializer
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    def post(self, request, boq_id):
        from apps.rbac.permissions import has_permission
        if not has_permission(request.user, 'boq', 'approve'):
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        boq = get_object_or_404(BOQ, id=boq_id)
        if boq.status == 'FINAL':
            return Response({'detail': 'BOQ already Approved'}, status=status.HTTP_400_BAD_REQUEST)
        boq.status = "FINAL"
        boq.approved_at = timezone.now()
        boq.save()
        from apps.boq.models import AuditLogEntry
        AuditLogEntry.objects.create(
            user=request.user,
            action="BOQ_APPROVED",
            reference_id=boq.id,
            details={"boq_id": boq.id, "version": boq.version}
        )
        return Response({'detail': f"BOQ v{boq.version} approved"}, status=status.HTTP_200_OK)


class BOQExportPDFAPI(APIView):
    authentication_classes = [QueryParamJWTAuthentication]
    permission_classes = [IsAdmin | IsFinance | IsEditor]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    def get(self, request, boq_id):
            from apps.boq.models import AuditLogEntry
            boq = get_object_or_404(BOQ, id=boq_id)
            user = request.user
            
            is_draft = boq.status == "DRAFT"
            
            # ERP RULE: Draft export is watermarked. Allowed for Editors.
            if is_draft:
                # Audit log mandatory for draft export
                AuditLogEntry.objects.create(
                    user=user,
                    action="EXPORT_DRAFT_BOQ",
                    details={"boq_id": boq.id, "version": boq.version}
                )
            
            pdf = BOQPDFBuilder(boq, is_draft=is_draft)
            return pdf.build()
        

class BOQExportExcelAPI(APIView):
    authentication_classes = [QueryParamJWTAuthentication]
    permission_classes = [IsAdmin | IsFinance]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    def get(self, request, boq_id):
        boq = get_object_or_404(BOQ, id=boq_id)
        
        # ✅ ERP HARD RULE: Only Final BOQs can be exported
        if boq.status != "FINAL":
            return Response(
                {"detail": "Only Final BOQs can be exported"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        return BOQExcelBuilder(boq).build()


class ApplyMarginAPI(APIView):
    permission_classes = [IsAdmin]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    def post(self, request, boq_id):
        boq = get_object_or_404(BOQ, id=boq_id)

        # ✅ ERP HARD RULE: No edits after approval
        if boq.status != "DRAFT":
            return Response(
                {"detail": "Cannot modify approved BOQ"},
                status=status.HTTP_403_FORBIDDEN
            )

        markup_pct = request.data.get("markup_pct")
        if markup_pct is None:
            return Response(
                {"detail": "markup_pct is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from decimal import Decimal
        markup_pct = Decimal(str(request.data.get("markup_pct")))
        
        for item in boq.items.all():
            item.markup_pct = markup_pct
            # Uses current unit_price which might have been overridden
            item.final_price = (
                item.unit_price * item.quantity * (1 + markup_pct / 100)
            )
            item.save()

        from apps.boq.models import AuditLogEntry
        AuditLogEntry.objects.create(
            user=request.user,
            action="MARGIN_APPLIED",
            details={"boq_id": boq.id, "version": boq.version, "markup_pct": float(markup_pct)}
        )

        return Response(
            {
                "detail": f"Margin {markup_pct}% applied successfully",
                "boq_id": boq.id
            },
            status=status.HTTP_200_OK
        )
    
class BOQItemPriceUpdateAPI(APIView):
    """
    API endpoint to update BOQItem unit_price (price override).
    
    Rules:
    - Only DRAFT BOQs can be modified
    - Recalculates final_price after override
    - Generates audit log entry
    - Master prices are never modified
    """
    permission_classes = [IsEditor]
    filter_backends = [SearchFilter, DjangoFilterBackend]

    def patch(self, request, boq_item_id):
        try:
            boq_item = get_object_or_404(BOQItem, id=boq_item_id)
            def patch(self, request, boq_item_id):
                boq_item = get_object_or_404(BOQItem, id=boq_item_id)
                boq = boq_item.boq
                if boq.status != "DRAFT":
                    return Response({"error": "Approved BOQ cannot be modified"}, status=400)
                from apps.boq.serializers import BOQItemPriceUpdateSerializer
                serializer = BOQItemPriceUpdateSerializer(data=request.data)
                if not serializer.is_valid():
                    return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                new_unit_price = serializer.validated_data['unit_price']
                old_unit_price = boq_item.unit_price
                boq_item.unit_price = new_unit_price
                boq_item.final_price = (boq_item.unit_price * boq_item.quantity * (1 + boq_item.markup_pct / 100))
                boq_item.save()
                item_ref = self._get_item_reference(boq_item)
                from apps.boq.models import AuditLogEntry
                AuditLogEntry.objects.create(
                    user=request.user,
                    action="PRICE UPDATE",
                    details={
                        "boq_id": boq.id,
                        "version": boq.version,
                        "boq_item_id": boq_item.id,
                        "item_reference": item_ref,
                        "old_unit_price": float(old_unit_price),
                        "new_unit_price": float(new_unit_price),
                        "area_name": boq_item.area.name if boq_item.area else "Unknown",
                        "quantity": boq_item.quantity,
                        "old_final_price": float(old_unit_price * boq_item.quantity * (1 + boq_item.markup_pct / 100)),
                        "new_final_price": float(boq_item.final_price)
                    }
                )
                return Response({
                    "detail": "BOQ item price updated successfully",
                    "boq_item_id": boq_item.id,
                    "unit_price": float(boq_item.unit_price),
                    "final_price": float(boq_item.final_price),
                    "item_reference": item_ref
                }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=400
            )

    def _get_item_reference(self, boq_item):
        """Generate human-readable reference for audit log"""
        if boq_item.item_type == "PRODUCT" and boq_item.product:
            return f"Product: {boq_item.product.make} ({boq_item.product.order_code})"
        elif boq_item.item_type == "DRIVER" and boq_item.driver:
            return f"Driver: {boq_item.driver.driver_code}"
        elif boq_item.item_type == "ACCESSORY" and boq_item.accessory:
            return f"Accessory: {boq_item.accessory.accessory_name}"
        else:
            return f"BOQ Item {boq_item.id}"

    
class BOQViewSet(ModelViewSet):
    """
    BOQ Management ViewSet with ERP-compliant deletion prevention.
    
    ERP RULES:
    ✅ BOQ cannot be deleted (audit compliance)
    ✅ Draft BOQ can be regenerated via GenerateBOQAPI
    ✅ Final BOQ is locked forever
    ✅ Full history is preserved for audit trail
    """
    queryset = BOQ.objects.all()
    serializer_class = BOQSerializer
    permission_classes = [IsEditorOrReadOnly]
    filter_backends = [SearchFilter, DjangoFilterBackend]

    def destroy(self, request, *args, **kwargs):
        """
        ERP RULE: Prevent deletion of BOQs.
        BOQs must NEVER be deleted (audit compliance).
        The system maintains a complete audit trail of all BOQs.
        """
        return Response(
            {
                "detail": "BOQs cannot be deleted (ERP audit compliance). "
                "The system maintains immutable audit trails. "
                "To generate a new BOQ, use the GenerateBOQAPI endpoint.",
                "status": "forbidden"
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
class BOQItemViewSet(ModelViewSet):
    permission_classes = [IsEditorOrReadOnly]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    queryset = BOQItem.objects.all()
    serializer_class = BOQItemSerializer

    def get_queryset(self):
        """Filter BOQ items by boq_id query parameter if provided"""
        queryset = BOQItem.objects.all()
        boq_id = self.request.query_params.get('boq_id')
        if boq_id:
            queryset = queryset.filter(boq_id=boq_id)
        return queryset

