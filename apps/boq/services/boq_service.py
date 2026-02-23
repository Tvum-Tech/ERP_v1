import io
import openpyxl
from decimal import Decimal
from datetime import date
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.db.models import Max

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT

from apps.boq.models import BOQ, BOQItem
from apps.projects.models import Project
from apps.configurations.models import (
    LightingConfiguration,
    ConfigurationAccessory,
    ConfigurationDriver
)

class BOQPDFBuilder:
    def __init__(self, boq, is_draft=False):
        self.boq = boq
        self.is_draft = is_draft
        self.buffer = io.BytesIO()
        self.pagesize = A4
        self.width, self.height = self.pagesize
        self.MARGIN_X = 15 * mm
        self.MARGIN_Y = 20 * mm
        self.styles = getSampleStyleSheet()
        self.style_normal = ParagraphStyle(
            'CreateNormal', parent=self.styles['Normal'], fontSize=8, leading=10
        )

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica-Bold', 14)
        canvas.drawString(self.MARGIN_X, self.height - 30, "TVUM TECH")
        canvas.setFont('Helvetica', 10)
        canvas.drawString(self.MARGIN_X, self.height - 45, "Lighting ERP – Bill of Quantities")
        canvas.setFont('Helvetica', 9)
        canvas.drawString(self.MARGIN_X, self.height - 65, f"Project: {self.boq.project.name}")
        canvas.drawRightString(self.width - self.MARGIN_X, self.height - 65, f"BOQ Version: {self.boq.version}")
        canvas.drawString(self.MARGIN_X, self.height - 80, f"Status: {self.boq.status}")
        canvas.drawRightString(self.width - self.MARGIN_X, self.height - 80, f"Date: {date.today().strftime('%d-%m-%Y')}")
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.5)
        canvas.line(self.MARGIN_X, self.height - 90, self.width - self.MARGIN_X, self.height - 90)
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(self.width / 2, 20, "System Generated BOQ | TVUM Lighting ERP")
        canvas.drawRightString(self.width - self.MARGIN_X, 20, f"Page {doc.page}")
        if self.is_draft:
            self._draw_watermark(canvas)
        canvas.restoreState()

    def _draw_watermark(self, canvas):
        canvas.saveState()
        canvas.setFont('Helvetica-Bold', 36)
        canvas.setStrokeColor(colors.lightgrey)
        canvas.setFillColor(colors.lightgrey, alpha=0.15)
        text = "DRAFT – INTERNAL ESTIMATE – NOT FOR CLIENT USE"
        canvas.translate(self.width/2, self.height/2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, text)
        canvas.restoreState()

    def _format_currency(self, value):
        return f"₹ {value:,.2f}"

    def build(self):
        doc = SimpleDocTemplate(
            self.buffer, pagesize=self.pagesize,
            leftMargin=self.MARGIN_X, rightMargin=self.MARGIN_X,
            topMargin=40 * mm, bottomMargin=30 * mm
        )
        elements = []
        grand_total = Decimal(0)
        # areas = self.boq.items.select_related("area").order_by("area__name").values_list("area__id", "area__name").distinct()
        areas = (
            self.boq.items
            .select_related("area")
            .values_list("area__id", "area__name")
            .distinct()
        )
        for area_id, area_name in areas:
            elements.append(Paragraph(f"<b>Area: {area_name}</b>", self.styles['Heading4']))
            elements.append(Spacer(1, 5))
            data = [["Type", "Item Code", "Description", "Qty", "Unit Rate", "Total"]]
            col_widths = [25*mm, 40*mm, 60*mm, 15*mm, 25*mm, 25*mm]
            area_total = Decimal(0)
            items = self.boq.items.filter(area_id=area_id)
            for item in items:
                qty = Decimal(item.quantity)
                selling_rate = Decimal(item.unit_price or 0) * (1 + Decimal(item.markup_pct or 0) / 100)
                line_total = Decimal(item.final_price or 0)
                area_total += line_total
                grand_total += line_total
                raw_desc = "-"
                item_code = "-"
                if item.item_type == "PRODUCT" and item.product:
                    raw_desc = item.product.make
                    item_code = item.product.order_code
                elif item.item_type == "DRIVER" and item.driver:
                    raw_desc = f"{item.driver.driver_make} - {item.driver.driver_code}"
                elif item.item_type == "ACCESSORY" and item.accessory:
                    raw_desc = item.accessory.accessory_name

                data.append([
                    item.item_type,
                    Paragraph(item_code, self.style_normal),
                    Paragraph(raw_desc, self.style_normal),
                    str(qty),
                    self._format_currency(selling_rate),
                    self._format_currency(line_total)
                ])
            data.append(["", "", "Area Subtotal:", "", "", self._format_currency(area_total)])
            table = Table(data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Grand Total: {self._format_currency(grand_total)}", ParagraphStyle('Total', parent=self.styles['Normal'], alignment=TA_RIGHT, fontSize=12, fontName='Helvetica-Bold')))
        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        self.buffer.seek(0)
        response = HttpResponse(self.buffer, content_type="application/pdf")
        filename = f"BOQ_{self.boq.project.name}_V{self.boq.version}_{self.boq.status}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

@transaction.atomic
def generate_boq(project, user):

    # -----------------------------
    # 1. Load Project
    # -----------------------------
    if not isinstance(project, Project):
        project = Project.objects.get(id=project)

    # -----------------------------
    # 2. Load Active Configurations
    # -----------------------------
    active_configs = LightingConfiguration.objects.filter(
        project=project,
        is_active=True
    ).select_related("area", "subarea", "product")

    if not active_configs.exists():
        raise ValidationError("No active configurations found.")

    # -----------------------------
    # 3. Detect Latest Configuration Change
    # -----------------------------
    latest_config_update = active_configs.aggregate(
        last_update=Max("updated_at")
    )["last_update"]

    latest_boq = BOQ.objects.filter(project=project).order_by("-version").first()

    if latest_boq and latest_boq.created_at >= latest_config_update:
        raise ValidationError("BOQ already generated for current configuration.")

    # -----------------------------
    # 4. Determine Next Version
    # -----------------------------
    latest_version = BOQ.objects.filter(project=project).aggregate(
        max_v=Max("version")
    )["max_v"] or 0

    next_version = latest_version + 1

    # -----------------------------
    # 5. Create BOQ Header
    # -----------------------------
    boq = BOQ.objects.create(
        project=project,
        version=next_version,
        created_by=user,
        status="DRAFT",
        source_configuration_version=next_version  # snapshot marker
    )

    # -----------------------------
    # 6. Create BOQ Items
    # -----------------------------
    seen_keys = set()

    for config in active_configs:

        area = config.area
        subarea = config.subarea
        product = config.product

        key = (
            area.id if area else None,
            subarea.id if subarea else None,
            product.pk
        )

        if key in seen_keys:
            continue

        seen_keys.add(key)

        product_price = product.base_price or 0
        product_total = product_price * config.quantity

        # PRODUCT
        BOQItem.objects.create(
            boq=boq,
            area=area,
            item_type="PRODUCT",
            product=product,
            quantity=config.quantity,
            unit_price=product_price,
            markup_pct=0,
            final_price=product_total,
        )

        # DRIVERS
        drivers = ConfigurationDriver.objects.filter(configuration=config)
        for drv in drivers:
            driver_price = drv.driver.base_price or 0
            BOQItem.objects.create(
                boq=boq,
                area=area,
                item_type="DRIVER",
                driver=drv.driver,
                quantity=drv.quantity,
                unit_price=driver_price,
                markup_pct=0,
                final_price=driver_price * drv.quantity,
            )

        # ACCESSORIES
        accessories = ConfigurationAccessory.objects.filter(configuration=config)
        for acc in accessories:
            acc_price = acc.accessory.base_price or 0
            BOQItem.objects.create(
                boq=boq,
                area=area,
                item_type="ACCESSORY",
                accessory=acc.accessory,
                quantity=acc.quantity,
                unit_price=acc_price,
                markup_pct=0,
                final_price=acc_price * acc.quantity,
            )

    return boq
def get_boq_summary(boq):
    if not boq:
        return None

    # 🔥 cumulative items
    items = BOQItem.objects.filter(
        boq__project=boq.project,
        boq__version__lte=boq.version
    ).values("item_type").annotate(
        total_qty=Sum("quantity"),
        total_value=Sum("final_price")
    )

    summary = {}
    for item in items:
        summary[item["item_type"]] = {
            "quantity": item["total_qty"],
            "amount": float(item["total_value"] or 0)
        }

    return {
        "project_id": boq.project.id,
        "boq_id": boq.id,
        "version": boq.version,
        "status": boq.status,
        "summary": summary,
        "created_at": boq.created_at,
        "source_configuration_version": boq.source_configuration_version
    }


def get_project_boq_summary(project):
    boq = BOQ.objects.filter(project=project).order_by("-version").first()
    return get_boq_summary(boq)

def approve_boq(boq):
    if boq.status != "DRAFT":
        raise ValidationError("Already finalized")
    boq.status = "FINAL"
    boq.locked_at = timezone.now()
    boq.save()
    return boq

def apply_margin_to_boq(boq, markup_pct):
    if boq.status != "DRAFT":
        raise ValidationError("Cannot modify FINAL BOQ")
    markup_pct = Decimal(markup_pct)
    for item in boq.items.all():
        item.markup_pct = markup_pct
        item.final_price = Decimal(item.unit_price) * Decimal(item.quantity) * (Decimal(1) + markup_pct / Decimal(100))
        item.save(update_fields=["markup_pct", "final_price"])
    return boq

class BOQExcelBuilder:
    def __init__(self, boq):
        self.boq = boq
        self.wb = openpyxl.Workbook()
        self.ws = self.wb.active
        self.ws.title = "BOQ"
        self.row = 1

    def money(self, value): return float(round(Decimal(value), 2))
    def bold(self): return openpyxl.styles.Font(bold=True)
    def center(self): return openpyxl.styles.Alignment(horizontal="center")
    def right(self): return openpyxl.styles.Alignment(horizontal="right")

    def write(self, col, value, bold=False, align=None, currency=False):
        cell = self.ws.cell(row=self.row, column=col, value=value)
        if bold: cell.font = self.bold()
        if align: cell.alignment = align
        if currency: cell.number_format = '₹#,##0.00'
        return cell

    def build(self):
        if self.boq.status != "FINAL": raise ValidationError("Excel export is allowed only for FINAL BOQ")
        self.write(1, "TVUM TECH", bold=True)
        self.row += 1
        self.write(1, "Lighting ERP – Bill of Quantities", bold=True)
        self.row += 2
        self.write(1, "Project:", bold=True); self.write(2, self.boq.project.name)
        self.write(5, "Version:", bold=True); self.write(6, self.boq.version)
        self.row += 1
        self.write(1, "Status:", bold=True); self.write(2, self.boq.status)
        self.write(5, "Date:", bold=True); self.write(6, date.today().strftime("%d-%m-%Y"))
        self.row += 2
        grand_total = Decimal(0)
        areas = self.boq.items.select_related("area").order_by("area__name").values_list("area__id", "area__name").distinct()
        for area_id, area_name in areas:
            self.write(1, f"Area: {area_name}", bold=True); self.row += 1
            headers = ["Type", "Item Code", "Description", "Qty", "Unit Price (₹)", "Margin (%)", "Line Total (₹)"]
            for col, h in enumerate(headers, start=1): self.write(col, h, bold=True, align=self.center())
            self.row += 1
            area_total = Decimal(0)
            for item in self.boq.items.filter(area_id=area_id):
                qty = Decimal(item.quantity)
                unit_price = Decimal(item.unit_price or 0)
                margin = Decimal(item.markup_pct or 0)
                line_total = Decimal(item.final_price or 0)
                area_total += line_total
                grand_total += line_total
                desc = "-"
                if item.item_type == "PRODUCT" and item.product: desc = item.product.make
                elif item.item_type == "DRIVER" and item.driver: desc = item.driver.driver_type
                elif item.item_type == "ACCESSORY" and item.accessory: desc = item.accessory.accessory_type
                self.write(1, item.item_type)
                self.write(2, item.product.order_code if item.product else "-")
                self.write(3, desc)
                self.write(4, int(qty), align=self.center())
                self.write(5, self.money(unit_price), align=self.right(), currency=True)
                self.write(6, float(margin), align=self.center())
                self.write(7, self.money(line_total), align=self.right(), currency=True)
                self.row += 1
            self.write(6, "Area Total", bold=True, align=self.right())
            self.write(7, self.money(area_total), bold=True, currency=True)
            self.row += 2
        self.write(6, "Grand Total", bold=True, align=self.right())
        self.write(7, self.money(grand_total), bold=True, currency=True)
        for col in range(1, 8): self.ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="BOQ_{self.boq.project.name}_V{self.boq.version}.xlsx"'
        self.wb.save(response)
        return response