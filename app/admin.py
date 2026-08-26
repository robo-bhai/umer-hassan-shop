from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin
from .models import *
from django.db.models import Sum, F, FloatField, DecimalField, ExpressionWrapper
from io import BytesIO
import datetime 
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.urls import reverse
from django.utils.html import format_html
from datetime import datetime, timedelta
import openpyxl
from django.template.loader import render_to_string
from openpyxl.styles import Font, Alignment
from openpyxl.worksheet.table import Table as ExcelTable, TableStyleInfo
from django.db import models
from decimal import Decimal
from django.contrib.admin.models import LogEntry
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
import os
from django.urls import path
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
import subprocess
from django.template.response import TemplateResponse
from django.http import HttpResponseForbidden
from django.utils.html import format_html
import io

BACKUP_DIR = "C:/Users/Store/P1/dbbackup/"

# ============================================
# REPORTLAB PDF GENERATION HELPER FUNCTIONS
# ============================================

def generate_invoice_pdf(sale_obj):
    """
    Sale ke liye proper Invoice PDF generate karein using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.3*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Company Info
    company = CompanyInfo.objects.first()
    company_name = company.name if company else "YOUR COMPANY NAME"
    company_address = company.address if company else "Address Here"
    company_phone = company.contact_number if company else "Phone"
    
    # Custom Styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    # Invoice Header
    story.append(Paragraph(company_name, title_style))
    story.append(Paragraph(company_address, styles['Normal']))
    story.append(Paragraph(f"Phone: {company_phone}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Invoice Title
    invoice_title = ParagraphStyle(
        'InvTitle',
        parent=styles['Heading2'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    story.append(Paragraph("TAX INVOICE", invoice_title))
    
    # Two-column layout for invoice details
    left_data = [
        [Paragraph(f"<b>Invoice No:</b> {sale_obj.bill_no}", styles['Normal'])],
        [Paragraph(f"<b>Date:</b> {sale_obj.sale_date.strftime('%d-%m-%Y')}", styles['Normal'])],
    ]
    
    right_data = [
        [Paragraph(f"<b>Customer:</b> {sale_obj.customer.name}", styles['Normal'])],
        [Paragraph(f"<b>Address:</b> {sale_obj.customer.address or '-'}", styles['Normal'])],
    ]
    
    left_table = Table(left_data, colWidths=[3*inch])
    right_table = Table(right_data, colWidths=[3*inch])
    
    left_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    right_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    header_table = Table([[left_table, right_table]], colWidths=[3.5*inch, 3.5*inch])
    story.append(header_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Items Table
    table_data = [['S.No', 'Product', 'Qty', 'Unit', 'Price', 'Discount', 'Total']]
    
    total_before_discount = Decimal('0.0')
    total_discount = Decimal('0.0')
    
    for idx, item in enumerate(sale_obj.saleitem_set.all(), 1):
        item_discount = item.discount if hasattr(item, 'discount') else Decimal('0.0')
        item_total = item.total_amt - item_discount
        table_data.append([
            str(idx),
            item.product.name,
            f"{item.qty:,.2f}",
            item.product.unit.name if item.product.unit else '-',
            f"{item.price:,.2f}",
            f"{item_discount:,.2f}",
            f"{item_total:,.2f}"
        ])
        total_before_discount += item.total_amt
        total_discount += item_discount
    
    # Summary Rows
    table_data.append(['', '', '', '', 'Subtotal:', '', f"{total_before_discount:,.2f}"])
    table_data.append(['', '', '', '', 'Discount:', '', f"{total_discount:,.2f}"])
    table_data.append(['', '', '', '', 'Grand Total:', '', f"{sale_obj.total_amount():,.2f}"])
    table_data.append(['', '', '', '', 'Paid:', '', f"{sale_obj.paid:,.2f}"])
    table_data.append(['', '', '', '', 'Outstanding:', '', f"{sale_obj.outstanding_balance():,.2f}"])
    
    col_widths = [0.5*inch, 2.5*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch, 1*inch]
    items_table = Table(table_data, repeatRows=1, colWidths=col_widths)
    
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -4), 0.5, colors.black),
        ('LINEBELOW', (4, -5), (-1, -5), 1, colors.black),
        ('FONTNAME', (0, -4), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    story.append(items_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer_text = company.footer_note if company and company.footer_note else "Thank you for your business!"
    story.append(Paragraph(footer_text, styles['Normal']))
    story.append(Paragraph("This is a computer generated invoice - no signature required.", styles['Normal']))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("<b>Terms & Conditions:</b>", styles['Normal']))
    story.append(Paragraph("1. Goods once sold will not be taken back.", styles['Normal']))
    story.append(Paragraph("2. All disputes subject to local jurisdiction.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


class CustomAdminSite(admin.AdminSite):
    """Custom Admin Site for Adding Backup/Restore/Delete View"""

    index_template = "admin/custom_index.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # Database Backup/Restore
            path('database-backup/', self.admin_view(self.database_backup_view), name='database-backup'),
            path('backup-db/', self.admin_view(self.backup_database), name='backup-db'),
            path('restore-db/', self.admin_view(self.restore_database), name='restore-db'),
            path('delete-backup/<str:filename>/', self.admin_view(self.delete_backup), name='delete-backup'),
            
            # Invoice & Documents
            path('invoice/<int:sale_id>/', self.admin_view(self.invoice_view), name='generate_invoice'),
            path('challan-pdf/<int:challan_id>/', self.admin_view(self.challan_pdf_view), name='generate_challan_pdf'),
            path('grn-pdf/<int:grn_id>/', self.admin_view(self.grn_pdf_view), name='generate_grn_pdf'),
            path('audit-pdf/<int:audit_id>/', self.admin_view(self.audit_pdf_view), name='generate_audit_pdf'),
            
            # Barcode
            path('find-product-by-barcode/', self.admin_view(self.find_product_by_barcode_view), name='find_product_by_barcode'),
            path('get-product-price/', self.admin_view(self.get_product_price_view), name='get_product_price'),
            path('app/product/supplier-barcode/', self.admin_view(self.supplier_barcode_view), name='supplier_barcode'),
            path('set-supplier-barcode/', self.admin_view(self.set_supplier_barcode), name='set_supplier_barcode'),
            
            # Status Updates
            path('app/saleorder/update-status/', self.admin_view(self.update_order_status_view), name='update_order_status'),
            path('app/purchaseorder/update-status/', self.admin_view(self.update_po_status_view), name='update_po_status'),
            
            # Dashboard
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
            path('dashboard/sales-forecast/', self.admin_view(self.sales_forecast_view), name='sales_forecast'),
            
            # System Health
            path('system-health/', self.admin_view(self.system_health_view), name='system-health'),
        ]
        return custom_urls + urls

    # ============================================
    # BACKUP METHODS
    # ============================================
    def get_backup_files(self):
        try:
            files = os.listdir(BACKUP_DIR)
            files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(BACKUP_DIR, x)), reverse=True)
            return files
        except FileNotFoundError:
            return []

    def database_backup_view(self, request):
        if not request.user.is_superuser:
            return HttpResponseForbidden("You are not allowed to access this page.")
        context = {
            **self.each_context(request),
            "title": "Database Backup",
            "backup_files": self.get_backup_files(),
            "backup_dir": BACKUP_DIR
        }
        return TemplateResponse(request, "admin/database_backup.html", context)

    def backup_database(self, request):
        try:
            subprocess.run(["python", "manage.py", "dbbackup"], check=True)
            messages.success(request, "✅ Database backup successfully created!")
        except subprocess.CalledProcessError:
            messages.error(request, "❌ Error while creating database backup.")
        return redirect("admin:database-backup")

    def restore_database(self, request):
        try:
            subprocess.run(["python", "manage.py", "dbrestore", "--noinput"], check=True)
            messages.success(request, "✅ Database restored successfully!")
        except subprocess.CalledProcessError:
            messages.error(request, "❌ Error while restoring database.")
        return redirect("admin:database-backup")

    def delete_backup(self, request, filename):
        file_path = os.path.join(BACKUP_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            messages.success(request, f"🗑️ Backup file '{filename}' deleted successfully!")
        else:
            messages.error(request, f"❌ Error: Backup file '{filename}' not found!")
        return redirect("admin:database-backup")

    # ============================================
    # DOCUMENT VIEWS
    # ============================================
    def invoice_view(self, request, sale_id):
        sale = get_object_or_404(Sale, pk=sale_id)
        pdf_buffer = generate_invoice_pdf(sale)
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="Invoice_{sale.bill_no}.pdf"'
        return response

    def challan_pdf_view(self, request, challan_id):
        from .models import DeliveryChallan
        challan = get_object_or_404(DeliveryChallan, pk=challan_id)
        admin_obj = DeliveryChallanAdmin(DeliveryChallan, self)
        return admin_obj.generate_challan_pdf(request, DeliveryChallan.objects.filter(pk=challan_id))

    def grn_pdf_view(self, request, grn_id):
        from .models import GoodsReceivedNote
        grn = get_object_or_404(GoodsReceivedNote, pk=grn_id)
        admin_obj = GoodsReceivedNoteAdmin(GoodsReceivedNote, self)
        return admin_obj.generate_grn_pdf(request, GoodsReceivedNote.objects.filter(pk=grn_id))

    def audit_pdf_view(self, request, audit_id):
        from .models import StockAudit
        audit = get_object_or_404(StockAudit, pk=audit_id)
        admin_obj = StockAuditAdmin(StockAudit, self)
        return admin_obj.generate_audit_pdf(request, StockAudit.objects.filter(pk=audit_id))

    # ============================================
    # BARCODE METHODS
    # ============================================
    def find_product_by_barcode_view(self, request):
        from django.http import JsonResponse
        from .models import Product
        import re
        barcode = request.GET.get('barcode', '').strip()
        barcode = re.sub(r'[^0-9]', '', barcode)
        if not barcode:
            return JsonResponse({'success': False, 'message': 'No barcode provided'})
        try:
            product = Product.objects.get(barcode=barcode)
            return JsonResponse({'success': True, 'product': {'id': product.id, 'name': product.name, 'barcode': product.barcode, 'price': str(product.price)}})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'})

    def get_product_price_view(self, request):
        from django.http import JsonResponse
        from .models import Product
        product_id = request.GET.get('product_id')
        if product_id:
            try:
                product = Product.objects.get(pk=product_id)
                return JsonResponse({'success': True, 'price': str(product.price), 'name': product.name})
            except Product.DoesNotExist:
                pass
        return JsonResponse({'success': False})

    def supplier_barcode_view(self, request):
        from django.shortcuts import render
        from .models import Product
        ids_str = request.GET.get('ids', '')
        product_ids = [int(id) for id in ids_str.split(',') if id]
        products = Product.objects.filter(id__in=product_ids)
        return render(request, "admin/supplier_barcode.html", {**self.each_context(request), "title": "Set Supplier Barcode", "products": products})

    def set_supplier_barcode(self, request):
        from django.http import JsonResponse
        from .models import Product
        import re
        product_id = request.POST.get('product_id')
        barcode = request.POST.get('barcode', '').strip()
        if not product_id or not barcode:
            return JsonResponse({'success': False, 'message': 'Missing data'})
        barcode = re.sub(r'[^0-9]', '', barcode)
        if not barcode:
            return JsonResponse({'success': False, 'message': 'Invalid barcode'})
        try:
            product = Product.objects.get(pk=product_id)
            if Product.objects.filter(barcode=barcode).exclude(pk=product_id).exists():
                return JsonResponse({'success': False, 'message': '❌ Already used by another product'})
            product.barcode = barcode
            product.use_custom_barcode = True
            product.save()
            return JsonResponse({'success': True, 'message': f'✅ Barcode set for {product.name}', 'barcode': barcode})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found'})

    # ============================================
    # STATUS UPDATE VIEWS
    # ============================================
    def update_order_status_view(self, request):
        from django.shortcuts import render
        from .models import SaleOrder
        ids_str = request.GET.get('ids', '')
        order_ids = [int(id) for id in ids_str.split(',') if id]
        orders = SaleOrder.objects.filter(id__in=order_ids)
        if request.method == 'POST':
            new_status = request.POST.get('status')
            if new_status:
                orders.update(status=new_status)
                messages.success(request, f"✅ Updated {orders.count()} orders")
                return redirect("admin:app_saleorder_changelist")
        return render(request, "admin/update_order_status.html", {**self.each_context(request), "title": "Update Order Status", "orders": orders, "status_choices": SaleOrder.ORDER_STATUS})

    def update_po_status_view(self, request):
        from django.shortcuts import render
        from .models import PurchaseOrder
        ids_str = request.GET.get('ids', '')
        po_ids = [int(id) for id in ids_str.split(',') if id]
        orders = PurchaseOrder.objects.filter(id__in=po_ids)
        if request.method == 'POST':
            new_status = request.POST.get('status')
            if new_status:
                orders.update(status=new_status)
                messages.success(request, f"✅ Updated {orders.count()} POs")
                return redirect("admin:app_purchaseorder_changelist")
        return render(request, "admin/update_po_status.html", {**self.each_context(request), "title": "Update PO Status", "orders": orders, "status_choices": PurchaseOrder.ORDER_STATUS})

    # ============================================
    # DASHBOARD
    # ============================================
    def dashboard_view(self, request):
        from datetime import timedelta, date
        from django.db.models import Sum
        import json
        today = date.today()
        month_ago = today - timedelta(days=30)
        daily_sales = []
        for i in range(30):
            d = today - timedelta(days=29-i)
            total = Sale.objects.filter(sale_date__date=d).aggregate(t=Sum('saleitem__total_amt'))['t'] or 0
            daily_sales.append({'date': d.strftime('%d %b'), 'amount': float(total)})
        top_products = SaleItem.objects.filter(sale__sale_date__gte=month_ago).values('product__name').annotate(total_qty=Sum('qty'), total_sales=Sum('total_amt')).order_by('-total_sales')[:10]
        slow_moving = []
        for inv in Inventory.objects.filter(stock__gt=0):
            sales_30d = SaleItem.objects.filter(product=inv.product, sale__sale_date__gte=month_ago).aggregate(t=Sum('qty'))['t'] or 0
            if sales_30d == 0 or (inv.stock > 0 and (sales_30d / inv.stock) < 0.1):
                slow_moving.append({'name': inv.product.name, 'stock': inv.stock, 'sales_30d': sales_30d, 'warehouse': inv.warehouse.name})
        today_cash = DailyCashFlow.objects.filter(date=today).first()
        if not today_cash:
            today_cash = DailyCashFlow(date=today)
            today_cash.calculate()
        weekly_cash = []
        for i in range(7):
            d = today - timedelta(days=6-i)
            cf = DailyCashFlow.objects.filter(date=d).first()
            if not cf:
                cf = DailyCashFlow(date=d)
                cf.calculate()
            weekly_cash.append({'date': d.strftime('%a'), 'cash_in': float(cf.cash_in), 'cash_out': float(cf.cash_out)})
        context = {
            **self.each_context(request), "title": "Dashboard",
            "daily_sales": json.dumps(daily_sales), "top_products": list(top_products),
            "slow_moving": slow_moving[:10], "today_cash": today_cash,
            "weekly_cash": json.dumps(weekly_cash),
            "total_customers": Customer.objects.count(), "total_products": Product.objects.count(),
            "total_sales_today": Sale.objects.filter(sale_date__date=today).count(),
            "total_purchase_today": Purchase.objects.filter(pur_date__date=today).count(),
            "low_stock_count": Inventory.objects.filter(stock__lt=F('product__low_stock_threshold')).count(),
        }
        return TemplateResponse(request, "admin/dashboard.html", context)

    def sales_forecast_view(self, request):
        from datetime import date, timedelta
        from django.db.models import Sum
        today = date.today()
        daily_data = []
        for i in range(90):
            d = today - timedelta(days=89-i)
            total = Sale.objects.filter(sale_date__date=d).aggregate(t=Sum('saleitem__total_amt'))['t'] or 0
            daily_data.append(float(total))
        forecast = []
        if len(daily_data) >= 7:
            for i in range(7):
                avg = sum(daily_data[-7:]) / 7
                next_date = today + timedelta(days=i+1)
                forecast.append({'date': next_date.strftime('%d %b'), 'amount': round(avg, 2)})
                daily_data.append(avg)
        return TemplateResponse(request, "admin/sales_forecast.html", {**self.each_context(request), "title": "Sales Forecast", "forecast": forecast})

    # ============================================
    # SYSTEM HEALTH (FULL FEATURED)
    # ============================================
    def system_health_view(self, request):
        import os
        from django.conf import settings
        from datetime import timedelta, date
        from django.db.models import Sum, Count
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        # CPU
        cpu_percent = 0
        cpu_count = 0
        cpu_freq = "N/A"
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpu_count = sum(1 for line in f if line.startswith('processor'))
            with open('/proc/stat', 'r') as f:
                cpu_line = f.readline()
                cpu_values = [int(x) for x in cpu_line.split()[1:8]]
                idle = cpu_values[3]
                total = sum(cpu_values)
                if total > 0:
                    cpu_percent = round(100 - (idle / total * 100), 1)
            try:
                with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq', 'r') as f:
                    freq_khz = int(f.read().strip())
                    cpu_freq = f"{round(freq_khz/1000, 1)} MHz"
            except: pass
        except: pass
        
        # RAM
        ram_total_gb = 0
        ram_used_gb = 0
        ram_free_gb = 0
        ram_percent = 0
        try:
            mem_info = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        mem_info[parts[0].strip()] = int(parts[1].strip().split()[0])
            total_kb = mem_info.get('MemTotal', 0)
            free_kb = mem_info.get('MemFree', 0)
            buffers_kb = mem_info.get('Buffers', 0)
            cached_kb = mem_info.get('Cached', 0)
            used_kb = total_kb - free_kb - buffers_kb - cached_kb
            ram_total_gb = round(total_kb / (1024**2), 2)
            ram_used_gb = round(used_kb / (1024**2), 2)
            ram_free_gb = round((free_kb + buffers_kb + cached_kb) / (1024**2), 2)
            if total_kb > 0: ram_percent = round((used_kb / total_kb) * 100, 1)
        except: pass
        
        # Disk
        disk_total_gb = 0
        disk_used_gb = 0
        disk_free_gb = 0
        disk_percent = 0
        try:
            stat = os.statvfs('/storage/emulated/0/')
            total_bytes = stat.f_frsize * stat.f_blocks
            free_bytes = stat.f_frsize * stat.f_bfree
            used_bytes = total_bytes - free_bytes
            disk_total_gb = round(total_bytes / (1024**3), 1)
            disk_used_gb = round(used_bytes / (1024**3), 1)
            disk_free_gb = round(free_bytes / (1024**3), 1)
            if total_bytes > 0: disk_percent = round((used_bytes / total_bytes) * 100, 1)
        except: pass
        
        # Database
        db_size_mb = 0
        try:
            if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path): db_size_mb = round(os.path.getsize(db_path) / (1024**2), 2)
        except: pass
        
        # Users & Sessions
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now()).count()
        active_users = User.objects.filter(is_active=True).count()
        
        # Failed Logins
        today = date.today()
        failed_logins = 0
        try:
            from axes.models import AccessAttempt
            failed_logins = AccessAttempt.objects.filter(attempt_time__date=today).count()
        except: pass
        
        # Model Counts
        model_counts = {
            'Products': Product.objects.count(), 'Customers': Customer.objects.count(),
            'Vendors': Vendor.objects.count(), 'Sales': Sale.objects.count(),
            'Purchases': Purchase.objects.count(), 'Sale Orders': SaleOrder.objects.count(),
            'Purchase Orders': PurchaseOrder.objects.count(), 'Challans': DeliveryChallan.objects.count(),
            'GRNs': GoodsReceivedNote.objects.count(), 'Inventory Items': Inventory.objects.count(),
            'Users': User.objects.count(),
        }
        total_records = sum(model_counts.values())
        
        # Recent Activity
        yesterday = now() - timedelta(hours=24)
        recent_sales = Sale.objects.filter(sale_date__gte=yesterday).count()
        recent_purchases = Purchase.objects.filter(pur_date__gte=yesterday).count()
        recent_orders = SaleOrder.objects.filter(order_date__gte=yesterday).count()
        recent_pos = PurchaseOrder.objects.filter(order_date__gte=yesterday).count()
        recent_challans = DeliveryChallan.objects.filter(challan_date__gte=yesterday).count()
        recent_grns = GoodsReceivedNote.objects.filter(grn_date__gte=yesterday).count()
        
        # Today's Summary
        today_sales_amount = Sale.objects.filter(sale_date__date=today).aggregate(t=Sum('saleitem__total_amt'))['t'] or Decimal('0.0')
        today_purchase_amount = Purchase.objects.filter(pur_date__date=today).aggregate(t=Sum('purchaseitem__total_amt'))['t'] or Decimal('0.0')
        today_collections = Sale.objects.filter(sale_date__date=today).aggregate(t=Sum('paid'))['t'] or Decimal('0.0')
        today_payments = Purchase.objects.filter(pur_date__date=today).aggregate(t=Sum('paid'))['t'] or Decimal('0.0')
        
        # Pending Tasks
        pending_orders = SaleOrder.objects.filter(status__in=['pending', 'confirmed', 'processing']).count()
        pending_deliveries = SaleOrder.objects.filter(status='ready').count()
        pending_pos = PurchaseOrder.objects.filter(status__in=['pending', 'confirmed']).count()
        low_stock_items = Inventory.objects.filter(stock__lt=F('product__low_stock_threshold')).count()
        
        # Logs
        recent_logs = LogEntry.objects.select_related('user').order_by('-action_time')[:15]
        
        # Backup
        last_backup = None
        try:
            backup_files = self.get_backup_files()
            if backup_files: last_backup = backup_files[0]
        except: pass
        
        license_valid = License.objects.filter(expiry_date__gte=now().date(), is_active=True).exists()
        import django, sys
        
        context = {
            **self.each_context(request), "title": "System Health",
            "cpu_percent": cpu_percent, "cpu_count": cpu_count, "cpu_freq": cpu_freq,
            "ram_total_gb": ram_total_gb, "ram_used_gb": ram_used_gb, "ram_free_gb": ram_free_gb, "ram_percent": ram_percent,
            "disk_total_gb": disk_total_gb, "disk_used_gb": disk_used_gb, "disk_free_gb": disk_free_gb, "disk_percent": disk_percent,
            "db_size_mb": db_size_mb, "total_records": total_records, "model_counts": model_counts,
            "active_sessions": active_sessions, "active_users": active_users, "failed_logins": failed_logins,
            "today_sales_amount": today_sales_amount, "today_purchase_amount": today_purchase_amount,
            "today_collections": today_collections, "today_payments": today_payments,
            "recent_sales": recent_sales, "recent_purchases": recent_purchases,
            "recent_orders": recent_orders, "recent_pos": recent_pos,
            "recent_challans": recent_challans, "recent_grns": recent_grns,
            "pending_orders": pending_orders, "pending_deliveries": pending_deliveries,
            "pending_pos": pending_pos, "low_stock_items": low_stock_items,
            "recent_logs": recent_logs, "last_backup": last_backup, "license_valid": license_valid,
            "django_version": django.get_version(), "python_version": sys.version.split()[0],
            "uptime_str": "N/A (Termux)",
        }
        return TemplateResponse(request, "admin/system_health.html", context)

# Default Admin Site کو CustomAdminSite سے Replace کریں
admin.site = CustomAdminSite()

admin.site.site_header = "Welcome"
admin.site.site_title = "Web App"
admin.site.index_title = "Admin Dashboard"


# SALE ORDER ITEM INLINE
# ============================================
class SaleOrderItemInline(admin.TabularInline):
    model = SaleOrderItem
    fields = ('product', 'qty', 'price', 'total_amt', 'reserved')
    readonly_fields = ('total_amt',)
    extra = 10


# ============================================
# SALE ORDER ADMIN
# ============================================
@admin.register(SaleOrder, site=admin.site)
class SaleOrderAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'order_date', 'customer', 'warehouse', 'status', 
                    'formatted_total', 'formatted_advance', 'formatted_outstanding', 
                    'delivery_status_display', 'converted_to_sale')
    list_filter = ('status', 'order_date', 'warehouse', 'customer__group')
    search_fields = ('order_no', 'customer__name', 'customer__contact_number')
    search_help_text = "Search by Order No, Customer Name, or Contact Number"
    inlines = [SaleOrderItemInline]
    change_list_template = "admin/button.html"
    actions = ['convert_to_sale', 'create_delivery_challan', 'update_status', 
               'generate_order_pdf', 'generate_order_html']
    
    readonly_fields = ('order_no', 'created_at', 'updated_at', 'converted_to_sale', 'created_by')
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_no', 'customer', 'warehouse', 'order_date', 'delivery_date', 'status')
        }),
        ('Payment Information', {
            'fields': ('discount_value', 'advance_payment')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at', 'converted_to_sale')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.status == 'invoiced':
            readonly.extend(['customer', 'warehouse', 'order_date', 'discount_value', 'advance_payment'])
        return readonly
    
    def formatted_total(self, obj):
        return f"Rs. {obj.total_amount():,.2f}"
    formatted_total.short_description = "Total"
    
    def formatted_advance(self, obj):
        return f"Rs. {obj.advance_payment:,.2f}"
    formatted_advance.short_description = "Advance"
    
    def formatted_outstanding(self, obj):
        return f"Rs. {obj.outstanding_advance():,.2f}"
    formatted_outstanding.short_description = "Outstanding"
    
    def delivery_status_display(self, obj):
        """Show delivery progress"""
        if obj.status in ['pending', 'confirmed']:
            return "Not Started"
        elif obj.status == 'partially_delivered':
            # Calculate percentage
            total_items = obj.items.count()
            if total_items > 0:
                delivered_count = 0
                for item in obj.items.all():
                    if obj.delivered_qty(item.product) >= item.qty:
                        delivered_count += 1
                percent = round((delivered_count / total_items) * 100)
                return format_html(
                    '<span style="color: #ff9800;">🟡 {}% Delivered</span>', percent
                )
            return "Partially Delivered"
        elif obj.status == 'delivered':
            return format_html('<span style="color: #28a745;">✅ Fully Delivered</span>')
        elif obj.status == 'invoiced':
            return format_html('<span style="color: #007bff;">📋 Invoiced</span>')
        elif obj.status == 'cancelled':
            return format_html('<span style="color: #dc3545;">❌ Cancelled</span>')
        return obj.get_status_display()
    delivery_status_display.short_description = "Delivery"
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def convert_to_sale(self, request, queryset):
        """Convert selected orders to Sale/Invoice"""
        from django.db import transaction
        
        success_count = 0
        error_messages = []
        
        for order in queryset.filter(status__in=['confirmed', 'ready', 'delivered', 'partially_delivered'], 
                                     converted_to_sale__isnull=True):
            try:
                with transaction.atomic():
                    sale = Sale.objects.create(
                        warehouse=order.warehouse,
                        bill_no=f"INV-{order.order_no}",
                        customer=order.customer,
                        sale_date=now(),
                        paid=order.advance_payment,
                        discount_value=order.discount_value,
                        created_by=request.user
                    )
                    
                    for item in order.items.all():
                        sale_item = SaleItem.objects.create(
                            sale=sale,
                            product=item.product,
                            qty=item.qty,
                            price=item.price
                        )
                        
                        if item.reserved:
                            try:
                                inventory = Inventory.objects.get(
                                    product=item.product, 
                                    warehouse=order.warehouse
                                )
                                inventory.reserved_stock = max(0, inventory.reserved_stock - item.qty)
                                inventory.save()
                            except Inventory.DoesNotExist:
                                pass
                    
                    order.status = 'invoiced'
                    order.converted_to_sale = sale
                    order.save()
                    
                    success_count += 1
                    
            except Exception as e:
                error_messages.append(f"Order {order.order_no}: {str(e)}")
        
        if success_count:
            self.message_user(request, f"✅ {success_count} orders converted to sale successfully.")
        if error_messages:
            self.message_user(request, f"❌ Errors: {'; '.join(error_messages)}", level=messages.ERROR)
    
    convert_to_sale.short_description = "🔄 Convert to Sale/Invoice"
    
    def create_delivery_challan(self, request, queryset):
        """Create Delivery Challan with Partial Delivery Support"""
        from django.db import transaction
        from django.db.models import Sum
        
        count = 0
        for order in queryset.filter(status__in=['confirmed', 'processing', 'ready', 'partially_delivered']):
            try:
                with transaction.atomic():
                    challan = DeliveryChallan.objects.create(
                        order=order,
                        customer=order.customer,
                        warehouse=order.warehouse,
                        reason='sale',
                        created_by=request.user
                    )
                    
                    for item in order.items.all():
                        # Calculate already delivered qty
                        already_delivered = DeliveryChallanItem.objects.filter(
                            challan__order=order,
                            product=item.product
                        ).aggregate(total=Sum('qty'))['total'] or 0
                        
                        pending = item.qty - already_delivered
                        
                        if pending > 0:
                            DeliveryChallanItem.objects.create(
                                challan=challan,
                                product=item.product,
                                order_qty=item.qty,
                                qty=pending,
                                price=item.price,
                                notes=f"Order: {order.order_no}"
                            )
                    
                    # Update order delivery status
                    order.update_delivery_status()
                    count += 1
                    
            except Exception as e:
                self.message_user(request, f"Error for {order.order_no}: {e}", level=messages.ERROR)
        
        if count:
            self.message_user(request, f"✅ {count} delivery challans created successfully.")
    
    create_delivery_challan.short_description = "📋 Create Delivery Challan"
    
    def update_status(self, request, queryset):
        """Bulk update order status"""
        selected_ids = queryset.values_list('id', flat=True)
        ids_str = ','.join(map(str, selected_ids))
        return redirect(f"/admin/app/saleorder/update-status/?ids={ids_str}")
    update_status.short_description = "📝 Update Status"
    
    def generate_order_pdf(self, request, queryset):
        """Generate PDF for selected orders"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        
        for order in queryset:
            story.append(Paragraph(f"Sale Order - {order.order_no}", styles['Heading1']))
            story.append(Paragraph(f"Customer: {order.customer.name}", styles['Normal']))
            story.append(Paragraph(f"Order Date: {order.order_date.strftime('%d-%m-%Y')}", styles['Normal']))
            story.append(Paragraph(f"Status: {order.get_status_display()}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            # Items table with delivery info
            data = [['Product', 'Order Qty', 'Delivered', 'Pending', 'Price', 'Total']]
            
            for item in order.items.all():
                delivered = order.delivered_qty(item.product)
                pending_qty = item.qty - delivered
                data.append([
                    item.product.name,
                    str(item.qty),
                    str(delivered),
                    str(pending_qty),
                    f"{item.price:,.2f}",
                    f"{item.total_amt:,.2f}"
                ])
            
            data.append(['', '', '', '', 'Total:', f"{order.total_amount():,.2f}"])
            data.append(['', '', '', '', 'Discount:', f"{order.discount_value:,.2f}"])
            data.append(['', '', '', '', 'Grand Total:', f"{order.total_after_discount():,.2f}"])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.5*inch))
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="sale_orders.pdf"'
        return response
    generate_order_pdf.short_description = "📄 Generate Order PDF"
    
    def generate_order_html(self, request, queryset):
        """Generate HTML report"""
        context = {'orders': queryset, 'date': datetime.now()}
        html = render_to_string('admin/sale_order_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="sale_orders.html"'
        return response
    generate_order_html.short_description = "🌐 Generate HTML Report"

class PurchaseRetrnItemInline(admin.TabularInline):
    model = PurchaseRetrnItem
    extra = 1


class SaleRetrnItemInline(admin.TabularInline):
    model = SaleRetrnItem
    extra = 1


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    fields = ('product', 'qty', 'price', 'total')
    extra = 10
    readonly_fields = ('total',)

    def total(self, obj):
        return Decimal(obj.qty) * Decimal(obj.price) if obj.qty and obj.price else 0
    total.short_description = 'Total'


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    fields = ('product', 'qty', 'price')
    extra = 10

# ============================================
# DELIVERY CHALLAN ITEM INLINE
# ============================================
class DeliveryChallanItemInline(admin.TabularInline):
    model = DeliveryChallanItem
    fields = ('product', 'order_qty', 'qty', 'pending_qty', 'unit', 'price', 'total_amt', 'notes')
    readonly_fields = ('pending_qty', 'total_amt')
    extra = 10


# ============================================
# DELIVERY CHALLAN ADMIN
# ============================================
@admin.register(DeliveryChallan, site=admin.site)
class DeliveryChallanAdmin(admin.ModelAdmin):
    list_display = ('challan_no', 'challan_date', 'customer', 'warehouse', 'order_link', 
                    'reason', 'total_qty_display', 'total_items_display', 'converted_to_sale', 'print_challan')
    list_filter = ('reason', 'challan_date', 'warehouse', 'converted_to_sale')
    search_fields = ('challan_no', 'customer__name', 'order__order_no')
    search_help_text = "Search by Challan No, Customer, or Order No"
    inlines = [DeliveryChallanItemInline]
    change_list_template = "admin/button.html"
    actions = ['generate_challan_pdf', 'convert_challan_to_sale']
    
    fieldsets = (
        ('Challan Information', {
            'fields': ('challan_no', 'order', 'customer', 'warehouse', 'challan_date', 'reason')
        }),
        ('Transport Details', {
            'fields': ('vehicle_no', 'transport_name', 'driver_name', 'driver_contact'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('notes',)
        }),
    )
    
    readonly_fields = ('challan_no',)
    
    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:app_saleorder_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_no)
        return "-"
    order_link.short_description = "Order"
    
    def total_qty_display(self, obj):
        return f"{obj.total_qty():,.2f}"
    total_qty_display.short_description = "Total Qty"
    
    def total_items_display(self, obj):
        return obj.total_items()
    total_items_display.short_description = "Items"
    
    def print_challan(self, obj):
        url = reverse('admin:generate_challan_pdf', args=[obj.pk])
        return format_html('<a href="{}" target="_blank">📄 Print</a>', url)
    print_challan.short_description = "Print"
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if obj.order and not obj.customer_id:
            obj.customer = obj.order.customer
        if obj.order and not obj.warehouse_id:
            obj.warehouse = obj.order.warehouse
        super().save_model(request, obj, form, change)
    
    def generate_challan_pdf(self, request, queryset):
        """Generate PDF for selected challans with Order Qty + Deliver Qty + Pending"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.3*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        company_address = company.address if company else "Address"
        company_phone = company.contact_number if company else "Phone"
        
        for challan in queryset:
            title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=5)
            story.append(Paragraph(company_name, title_style))
            story.append(Paragraph(company_address, styles['Normal']))
            story.append(Paragraph(f"Phone: {company_phone}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            story.append(Paragraph("<b>DELIVERY CHALLAN</b>", title_style))
            story.append(Spacer(1, 0.15*inch))
            
            details_data = [
                [Paragraph(f"<b>Challan No:</b> {challan.challan_no}", styles['Normal']),
                 Paragraph(f"<b>Date:</b> {challan.challan_date.strftime('%d-%m-%Y')}", styles['Normal'])],
                [Paragraph(f"<b>Order No:</b> {challan.order.order_no if challan.order else 'N/A'}", styles['Normal']),
                 Paragraph(f"<b>Vehicle No:</b> {challan.vehicle_no or '_________'}", styles['Normal'])],
                [Paragraph(f"<b>Reason:</b> {challan.get_reason_display()}", styles['Normal']),
                 Paragraph(f"<b>Transport:</b> {challan.transport_name or '_________'}", styles['Normal'])],
            ]
            
            details_table = Table(details_data, colWidths=[3.5*inch, 3.5*inch])
            details_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(details_table)
            
            from_to_data = [
                [Paragraph("<b>From:</b>", styles['Normal']), Paragraph("<b>To:</b>", styles['Normal'])],
                [Paragraph(company_name + "<br/>" + company_address + "<br/>Phone: " + company_phone, styles['Normal']),
                 Paragraph(f"{challan.customer.name}<br/>{challan.customer.address or ''}<br/>Contact: {challan.customer.contact_number or ''}", styles['Normal'])],
            ]
            
            from_to_table = Table(from_to_data, colWidths=[3.5*inch, 3.5*inch])
            from_to_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LINEBELOW', (0, 1), (-1, 1), 0.5, colors.grey),
            ]))
            story.append(from_to_table)
            story.append(Spacer(1, 0.2*inch))
            
            # ✅ Updated Items Table with Order Qty + Deliver Qty + Pending
            table_data = [['S.No', 'Product', 'Order Qty', 'Deliver Qty', 'Pending', 'Unit', 'Remarks']]
            
            total_order = 0
            total_deliver = 0
            total_pending = 0
            
            for idx, item in enumerate(challan.items.all(), 1):
                table_data.append([
                    str(idx),
                    item.product.name,
                    f"{item.order_qty:,.2f}",
                    f"{item.qty:,.2f}",
                    f"{item.pending_qty:,.2f}",
                    item.unit or '-',
                    item.notes or ''
                ])
                total_order += item.order_qty
                total_deliver += item.qty
                total_pending += item.pending_qty
            
            table_data.append(['', 'TOTAL', f"{total_order:,.2f}", f"{total_deliver:,.2f}", f"{total_pending:,.2f}", '', f"{challan.total_items()} items"])
            
            col_widths = [0.4*inch, 1.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.7*inch, 1.2*inch]
            items_table = Table(table_data, repeatRows=1, colWidths=col_widths)
            
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -2), 'LEFT'),
                ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 0.4*inch))
            
            sign_data = [
                [Paragraph("<b>Received by:</b> _________________", styles['Normal']),
                 Paragraph("<b>Dispatched by:</b> _________________", styles['Normal'])],
                [Paragraph("Signature: _________________", styles['Normal']),
                 Paragraph("Signature: _________________", styles['Normal'])],
                [Paragraph("Date: _________________", styles['Normal']),
                 Paragraph("Date: _________________", styles['Normal'])],
            ]
            
            sign_table = Table(sign_data, colWidths=[3.5*inch, 3.5*inch])
            sign_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(sign_table)
            
            story.append(Spacer(1, 0.3*inch))
            story.append(Paragraph("This is a computer generated challan - no signature required.", styles['Normal']))
            story.append(Paragraph("<br/><br/>", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="delivery_challan.pdf"'
        return response
    generate_challan_pdf.short_description = "📄 Generate Challan PDF"
    
    def convert_challan_to_sale(self, request, queryset):
        """Convert challan to Sale/Invoice"""
        from django.db import transaction
        
        count = 0
        for challan in queryset.filter(converted_to_sale=False):
            try:
                with transaction.atomic():
                    sale = Sale.objects.create(
                        warehouse=challan.warehouse,
                        bill_no=f"INV-{challan.challan_no}",
                        customer=challan.customer,
                        sale_date=now(),
                        created_by=request.user
                    )
                    
                    for item in challan.items.all():
                        SaleItem.objects.create(
                            sale=sale,
                            product=item.product,
                            qty=item.qty,
                            price=item.price
                        )
                    
                    challan.converted_to_sale = True
                    challan.save()
                    count += 1
            except Exception as e:
                self.message_user(request, f"Error: {e}", level=messages.ERROR)
        
        if count:
            self.message_user(request, f"✅ {count} challans converted to sale.")
    convert_challan_to_sale.short_description = "🔄 Convert to Sale/Invoice"

@admin.register(Warehouse, site=admin.site)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'description')
    search_fields = ('name',)
    list_filter = ('location',)
    change_list_template = "admin/button.html"


@admin.register(WarehouseTransfer, site=admin.site)
class WarehouseTransferAdmin(admin.ModelAdmin):
    list_display = ('transfer_date', 'product', 'from_warehouse', 'to_warehouse', 'qty', 'created_by')
    list_filter = ('from_warehouse', 'to_warehouse', 'transfer_date')
    search_fields = ('product__name',)
    change_list_template = "admin/button.html"
    actions = ['generate_transfer_report', 'generate_transfer_pdf']

    def generate_transfer_report(self, request, queryset):
        """Generate HTML report for selected transfers."""
        context = {
            'transfers': queryset,
            'date': datetime.now()
        }
        html = render_to_string('admin/warehouse_transfer_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="warehouse_transfer_report.html"'
        return response
    generate_transfer_report.short_description = "Generate Transfer Report (HTML)"
    
    def generate_transfer_pdf(self, request, queryset):
        """Generate PDF report for warehouse transfers."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=10)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Warehouse Transfer Report", title_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Date', 'Product', 'From Warehouse', 'To Warehouse', 'Quantity', 'Transferred By']]
        
        for transfer in queryset:
            table_data.append([
                transfer.transfer_date.strftime('%d-%m-%Y'),
                transfer.product.name,
                transfer.from_warehouse.name,
                transfer.to_warehouse.name,
                f"{transfer.qty:,.2f}",
                transfer.created_by.username if transfer.created_by else '-'
            ])
        
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="warehouse_transfer_report.pdf"'
        return response
    generate_transfer_pdf.short_description = "Generate Transfer Report (PDF)"


from django.urls import reverse
from django.utils.html import format_html
#from .barcode_utils import generate_barcode_image, generate_barcode_label, generate_multiple_labels
from django.http import HttpResponse
import io

@admin.register(Product, site=admin.site)
class ProductAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    search_fields = ('serial_no', 'name', 'barcode')
    search_help_text = "Search by Serial No, Product Name, Barcode"
    list_display = ('serial_no', 'name', 'barcode', 'barcode_preview', 'use_custom_barcode', 
                    'description', 'unit', 'location', 'price', 'used', 'brand', 'category', 
                    'types', 'low_stock_threshold')
    ordering = ('serial_no',)
    change_list_template = "admin/button.html"
    actions = ['generate_barcodes', 'print_barcode_labels', 'print_selected_labels', 'print_single_labels', 'scan_supplier_barcode']
    
    # Fieldsets - price hataya gaya kyunke editable=False hai
    fieldsets = (
        ('Basic Information', {
            'fields': ('serial_no', 'name', 'description', 'used')
        }),
        ('Barcode Information', {
            'fields': ('use_custom_barcode', 'barcode'),
            'description': 'Check "Use Custom/Supplier Barcode" to manually enter supplier barcode instead of auto-generating.'
        }),
        ('Categorization', {
            'fields': ('unit', 'brand', 'category', 'types', 'location')
        }),
        ('Stock Settings', {
            'fields': ('low_stock_threshold',),
            'description': 'Set minimum stock level for alerts.'
        }),
    )
    
    # Price ko readonly_fields mein add karein
    readonly_fields = ('price',)
    
    def get_readonly_fields(self, request, obj=None):
        """Make barcode readonly if use_custom_barcode is False"""
        readonly = list(self.readonly_fields)
        if obj and not obj.use_custom_barcode:
            readonly.append('barcode')
        return readonly
    
    def changelist_view(self, request, extra_context=None):
        """Add has_barcode_action flag to context"""
        extra_context = extra_context or {}
        extra_context['has_barcode_action'] = True
        return super().changelist_view(request, extra_context=extra_context)
    
    def barcode_preview(self, obj):
        """Show barcode image in admin list"""
        if obj.barcode:
            try:
                barcode_img = generate_barcode_image(obj.barcode)
                if barcode_img:
                    return format_html('<img src="{}" width="150" height="50">', barcode_img)
                return obj.barcode
            except Exception as e:
                return obj.barcode
        return "No Barcode"
    barcode_preview.short_description = "Barcode Preview"
    
    def generate_barcodes(self, request, queryset):
        """Generate barcodes for selected products that don't have one AND don't use custom barcode"""
        count = 0
        for product in queryset.filter(barcode__isnull=True, use_custom_barcode=False):
            product.save()
            count += 1
        self.message_user(request, f"Generated barcodes for {count} products.")
    generate_barcodes.short_description = "🔄 Generate Barcodes for Selected"
    
    def scan_supplier_barcode(self, request, queryset):
        """Action to open barcode scanner for supplier barcode"""
        selected_ids = queryset.values_list('id', flat=True)
        ids_str = ','.join(map(str, selected_ids))
        return redirect(f"/admin/app/product/supplier-barcode/?ids={ids_str}")
    scan_supplier_barcode.short_description = "🏷️ Scan/Set Supplier Barcode"
    
    def print_barcode_labels(self, request, queryset):
        """Generate PDF with barcode labels for selected products"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.3*inch, bottomMargin=0.3*inch)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph("Barcode Labels", styles['Heading1']))
        story.append(Spacer(1, 0.2*inch))
        
        table_data = []
        row = []
        
        for i, product in enumerate(queryset):
            if not product.barcode:
                product.save()
            
            barcode_img_data = generate_barcode_image(product.barcode)
            
            if not barcode_img_data:
                barcode_img_data = ""
            
            cell_content = Paragraph(
                f"<b>{product.name[:20]}</b><br/>"
                f"<img src='{barcode_img_data}' width='120' height='40'/><br/>"
                f"{product.barcode}<br/>"
                f"Rs. {product.price:,.2f}",
                styles['Normal']
            )
            
            row.append(cell_content)
            
            if len(row) == 3 or i == queryset.count() - 1:
                while len(row) < 3:
                    row.append("")
                table_data.append(row)
                row = []
        
        if table_data:
            table = Table(table_data, colWidths=[2.5*inch, 2.5*inch, 2.5*inch])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            
            story.append(table)
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="barcode_labels.pdf"'
        return response
    print_barcode_labels.short_description = "📄 Print Barcode Labels (PDF)"
    
    def print_selected_labels(self, request, queryset):
        """Print labels as PNG image sheet"""
        products_data = []
        for product in queryset:
            if not product.barcode:
                product.save()
            products_data.append({
                'barcode': product.barcode,
                'name': product.name,
                'price': str(product.price)
            })
        
        buffer = generate_multiple_labels(products_data)
        
        response = HttpResponse(buffer, content_type='image/png')
        response['Content-Disposition'] = 'attachment; filename="barcode_labels_sheet.png"'
        return response
    print_selected_labels.short_description = "🖼️ Print Labels Sheet (PNG)"
    
    def print_single_labels(self, request, queryset):
        """Print individual labels one per page"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        for product in queryset:
            if not product.barcode:
                product.save()
            
            barcode_img = generate_barcode_image(product.barcode)
            
            story.append(Paragraph(f"<b>{product.name}</b>", styles['Heading2']))
            if barcode_img:
                story.append(Paragraph(f"<img src='{barcode_img}' width='200' height='60'/>", styles['Normal']))
            story.append(Paragraph(f"Barcode: {product.barcode}", styles['Normal']))
            story.append(Paragraph(f"Price: Rs. {product.price:,.2f}", styles['Normal']))
            story.append(Spacer(1, 0.5*inch))
            story.append(Paragraph("- - - - - - - - - - - - - - - - - - - -", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="single_barcode_labels.pdf"'
        return response
    print_single_labels.short_description = "🏷️ Print Single Labels (One per page)"


# ============================================
# VENDOR GROUP ADMIN
# ============================================
@admin.register(VendorGroup, site=admin.site)
class VendorGroupAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    search_help_text = "Search by Vendor Group Name"
    list_display = ['name', 'description', 'total_outstanding_balance_display']
    change_list_template = "admin/button.html"
    actions = ['generate_html_report', 'generate_vendor_group_pdf']

    def total_outstanding_balance_display(self, obj):
        return f'{obj.total_outstanding_balance():,.2f}'
    total_outstanding_balance_display.short_description = 'Total Outstanding Balance'

    def generate_html_report(self, request, queryset):
        VendorGroups = queryset
        context = {'VendorGroups': VendorGroups, 'date': datetime.now()}
        html = render_to_string('admin/VendorGroup_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="VendorGroup_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'
    
    def generate_vendor_group_pdf(self, request, queryset):
        """Generate PDF report for Vendor Groups."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Vendor Group Report", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Group Name', 'Description', 'Outstanding Balance']]
        
        for group in queryset:
            table_data.append([
                group.name,
                group.description or '-',
                f"{group.total_outstanding_balance():,.2f}"
            ])
        
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="vendor_group_report.pdf"'
        return response
    generate_vendor_group_pdf.short_description = 'Generate PDF Report'


# ============================================
# VENDOR ADMIN
# ============================================
@admin.register(Vendor, site=admin.site)
class VendorAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    search_help_text = "Search by Vendor Name"
    list_display = ('name','group', 'contact_number', 'address', 'formatted_outstanding_balance')
    ordering = ('name',)
    change_list_template = "admin/button.html"
    actions = ['generate_html_report', 'generate_vendor_pdf']

    def formatted_outstanding_balance(self, obj):
        return f"{obj.outstanding_balance():,.2f} PKR"
    formatted_outstanding_balance.short_description = "Outstanding Balance"

    def generate_html_report(self, request, queryset):
        vendors = queryset
        context = {'vendors': vendors, 'date': datetime.now()}
        html = render_to_string('admin/vendor_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="vendor_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'
    
    def generate_vendor_pdf(self, request, queryset):
        """Generate PDF report for Vendors."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=10)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Vendor Report", title_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Name', 'Group', 'Contact', 'Address', 'Outstanding Balance']]
        
        total_outstanding = Decimal('0.0')
        for vendor in queryset:
            balance = vendor.outstanding_balance()
            table_data.append([
                vendor.name,
                vendor.group.name if vendor.group else '-',
                vendor.contact_number or '-',
                (vendor.address[:30] + '...') if vendor.address and len(vendor.address) > 30 else (vendor.address or '-'),
                f"{balance:,.2f}"
            ])
            total_outstanding += balance
        
        table_data.append(['', '', '', 'TOTAL:', f"{total_outstanding:,.2f}"])
        
        table = Table(table_data, repeatRows=1, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 2*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="vendor_report.pdf"'
        return response
    generate_vendor_pdf.short_description = 'Generate PDF Report'
    
# ============================================
# PURCHASE ORDER ITEM INLINE
# ============================================
class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    fields = ('product', 'qty', 'price', 'total_amt')
    readonly_fields = ('total_amt',)
    extra = 10


# ============================================
# PURCHASE ORDER ADMIN
# ============================================
@admin.register(PurchaseOrder, site=admin.site)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'order_date', 'vendor', 'warehouse', 'status',
                    'formatted_total', 'formatted_advance', 'formatted_outstanding',
                    'receive_status_display', 'converted_to_purchase')
    list_filter = ('status', 'order_date', 'warehouse', 'vendor__group')
    search_fields = ('order_no', 'vendor__name')
    search_help_text = "Search by PO Number or Vendor Name"
    inlines = [PurchaseOrderItemInline]
    change_list_template = "admin/button.html"
    actions = ['convert_to_purchase', 'create_grn', 'update_po_status', 'generate_po_pdf']
    
    readonly_fields = ('order_no', 'created_at', 'updated_at', 'converted_to_purchase', 'created_by')
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_no', 'vendor', 'warehouse', 'order_date', 'expected_date', 'status')
        }),
        ('Payment Information', {
            'fields': ('discount_value', 'advance_payment')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_at', 'updated_at', 'converted_to_purchase')
        }),
    )
    
    def formatted_total(self, obj):
        return f"Rs. {obj.total_amount():,.2f}"
    formatted_total.short_description = "Total"
    
    def formatted_advance(self, obj):
        return f"Rs. {obj.advance_payment:,.2f}"
    formatted_advance.short_description = "Advance"
    
    def formatted_outstanding(self, obj):
        return f"Rs. {obj.outstanding_advance():,.2f}"
    formatted_outstanding.short_description = "Outstanding"
    
    def receive_status_display(self, obj):
        if obj.status in ['pending', 'confirmed']:
            return "Not Received"
        elif obj.status == 'partially_received':
            total_items = obj.items.count()
            if total_items > 0:
                received_count = sum(1 for item in obj.items.all() if obj.received_qty(item.product) >= item.qty)
                percent = round((received_count / total_items) * 100)
                return format_html('<span style="color: #ff9800;">🟡 {}% Received</span>', percent)
            return "Partially Received"
        elif obj.status == 'received':
            return format_html('<span style="color: #28a745;">✅ Received</span>')
        elif obj.status == 'completed':
            return format_html('<span style="color: #007bff;">📋 Completed</span>')
        elif obj.status == 'cancelled':
            return format_html('<span style="color: #dc3545;">❌ Cancelled</span>')
        return obj.get_status_display()
    receive_status_display.short_description = "Receive Status"
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def convert_to_purchase(self, request, queryset):
        """Convert selected POs to Purchase"""
        success_count = 0
        for order in queryset.filter(status__in=['received', 'partially_received'], converted_to_purchase__isnull=True):
            try:
                with transaction.atomic():
                    purchase = Purchase.objects.create(
                        warehouse=order.warehouse,
                        bill_no=f"BILL-{order.order_no}",
                        vendor=order.vendor,
                        pur_date=now(),
                        paid=order.advance_payment,
                        created_by=request.user
                    )
                    
                    for item in order.items.all():
                        PurchaseItem.objects.create(
                            purchase=purchase,
                            product=item.product,
                            qty=item.qty,
                            price=item.price
                        )
                    
                    order.status = 'completed'
                    order.converted_to_purchase = purchase
                    order.save()
                    success_count += 1
            except Exception as e:
                self.message_user(request, f"Error: {e}", level=messages.ERROR)
        
        if success_count:
            self.message_user(request, f"✅ {success_count} POs converted to purchase.")
    convert_to_purchase.short_description = "🔄 Convert to Purchase"
    
    def create_grn(self, request, queryset):
        """Create GRN from selected POs"""
        from django.db.models import Sum
        
        count = 0
        for order in queryset.filter(status__in=['confirmed', 'processing', 'shipped', 'partially_received']):
            try:
                with transaction.atomic():
                    grn = GoodsReceivedNote.objects.create(
                        purchase_order=order,
                        vendor=order.vendor,
                        warehouse=order.warehouse,
                        reason='purchase',
                        created_by=request.user
                    )
                    
                    for item in order.items.all():
                        already_received = GoodsReceivedItem.objects.filter(
                            grn__purchase_order=order,
                            product=item.product
                        ).aggregate(total=Sum('qty'))['total'] or 0
                        
                        pending = item.qty - already_received
                        
                        if pending > 0:
                            GoodsReceivedItem.objects.create(
                                grn=grn,
                                product=item.product,
                                order_qty=item.qty,
                                qty=pending,
                                price=item.price,
                                notes=f"PO: {order.order_no}"
                            )
                    
                    order.update_receive_status()
                    count += 1
            except Exception as e:
                self.message_user(request, f"Error: {e}", level=messages.ERROR)
        
        if count:
            self.message_user(request, f"✅ {count} GRNs created successfully.")
    create_grn.short_description = "📋 Create GRN (Receive Goods)"
    
    def update_po_status(self, request, queryset):
        selected_ids = queryset.values_list('id', flat=True)
        ids_str = ','.join(map(str, selected_ids))
        return redirect(f"/admin/app/purchaseorder/update-status/?ids={ids_str}")
    update_po_status.short_description = "📝 Update Status"
    
    def generate_po_pdf(self, request, queryset):
        """Generate PDF for POs"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        for order in queryset:
            story.append(Paragraph(f"Purchase Order - {order.order_no}", styles['Heading1']))
            story.append(Paragraph(f"Vendor: {order.vendor.name}", styles['Normal']))
            story.append(Paragraph(f"Status: {order.get_status_display()}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
            
            data = [['Product', 'Order Qty', 'Received', 'Pending', 'Price', 'Total']]
            for item in order.items.all():
                received = order.received_qty(item.product)
                data.append([item.product.name, str(item.qty), str(received), str(item.qty - received), f"{item.price:,.2f}", f"{item.total_amt:,.2f}"])
            
            data.append(['', '', '', '', 'Total:', f"{order.total_amount():,.2f}"])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.5*inch))
        
        doc.build(story)
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf')
    generate_po_pdf.short_description = "📄 Generate PO PDF"


# ============================================
# GRN ITEM INLINE
# ============================================
class GoodsReceivedItemInline(admin.TabularInline):
    model = GoodsReceivedItem
    fields = ('product', 'order_qty', 'qty', 'pending_qty', 'unit', 'price', 'total_amt', 'notes')
    readonly_fields = ('pending_qty', 'total_amt')
    extra = 10


# ============================================
# GRN ADMIN
# ============================================
@admin.register(GoodsReceivedNote, site=admin.site)
class GoodsReceivedNoteAdmin(admin.ModelAdmin):
    list_display = ('grn_no', 'grn_date', 'vendor', 'warehouse', 'po_link',
                    'reason', 'total_qty_display', 'total_items_display', 'converted_to_purchase', 'print_grn')
    list_filter = ('reason', 'grn_date', 'warehouse')
    search_fields = ('grn_no', 'vendor__name', 'purchase_order__order_no')
    inlines = [GoodsReceivedItemInline]
    change_list_template = "admin/button.html"
    actions = ['generate_grn_pdf', 'convert_grn_to_purchase']
    
    fieldsets = (
        ('GRN Information', {
            'fields': ('grn_no', 'purchase_order', 'vendor', 'warehouse', 'grn_date', 'reason')
        }),
        ('Supplier Invoice', {
            'fields': ('invoice_no',)
        }),
        ('Transport', {
            'fields': ('vehicle_no', 'driver_name'),
            'classes': ('collapse',)
        }),
        ('Remarks', {
            'fields': ('notes',)
        }),
    )
    
    readonly_fields = ('grn_no',)
    
    def po_link(self, obj):
        if obj.purchase_order:
            url = reverse('admin:app_purchaseorder_change', args=[obj.purchase_order.id])
            return format_html('<a href="{}">{}</a>', url, obj.purchase_order.order_no)
        return "-"
    po_link.short_description = "PO"
    
    def total_qty_display(self, obj):
        return f"{obj.total_qty():,.2f}"
    total_qty_display.short_description = "Total Qty"
    
    def total_items_display(self, obj):
        return obj.total_items()
    total_items_display.short_description = "Items"
    
    def print_grn(self, obj):
        url = reverse('admin:generate_grn_pdf', args=[obj.pk])
        return format_html('<a href="{}" target="_blank">📄 Print</a>', url)
    print_grn.short_description = "Print"
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if obj.purchase_order and not obj.vendor_id:
            obj.vendor = obj.purchase_order.vendor
        if obj.purchase_order and not obj.warehouse_id:
            obj.warehouse = obj.purchase_order.warehouse
        super().save_model(request, obj, form, change)
    
    def generate_grn_pdf(self, request, queryset):
        """Generate PDF for GRNs"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.3*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        for grn in queryset:
            title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER)
            story.append(Paragraph(company_name, title_style))
            story.append(Paragraph("<b>GOODS RECEIVED NOTE (GRN)</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            details = [
                [Paragraph(f"<b>GRN No:</b> {grn.grn_no}"), Paragraph(f"<b>Date:</b> {grn.grn_date.strftime('%d-%m-%Y')}")],
                [Paragraph(f"<b>PO No:</b> {grn.purchase_order.order_no if grn.purchase_order else 'N/A'}"), Paragraph(f"<b>Invoice:</b> {grn.invoice_no or 'N/A'}")],
                [Paragraph(f"<b>Vendor:</b> {grn.vendor.name}"), Paragraph(f"<b>Vehicle:</b> {grn.vehicle_no or 'N/A'}")],
            ]
            t = Table(details, colWidths=[3.5*inch, 3.5*inch])
            story.append(t)
            story.append(Spacer(1, 0.2*inch))
            
            table_data = [['S.No', 'Product', 'Order Qty', 'Received', 'Pending', 'Unit']]
            total_order = 0
            total_rec = 0
            total_pend = 0
            
            for idx, item in enumerate(grn.items.all(), 1):
                table_data.append([str(idx), item.product.name, f"{item.order_qty:,.2f}", f"{item.qty:,.2f}", f"{item.pending_qty:,.2f}", item.unit or '-'])
                total_order += item.order_qty
                total_rec += item.qty
                total_pend += item.pending_qty
            
            table_data.append(['', 'TOTAL', f"{total_order:,.2f}", f"{total_rec:,.2f}", f"{total_pend:,.2f}", ''])
            
            items_table = Table(table_data, repeatRows=1)
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            story.append(items_table)
            story.append(Spacer(1, 0.4*inch))
            
            sign = [
                [Paragraph("<b>Received by:</b> _________"), Paragraph("<b>Checked by:</b> _________")],
            ]
            story.append(Table(sign, colWidths=[3.5*inch, 3.5*inch]))
            story.append(Paragraph("<br/><br/>", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf')
    generate_grn_pdf.short_description = "📄 Generate GRN PDF"
    
    def convert_grn_to_purchase(self, request, queryset):
        count = 0
        for grn in queryset.filter(converted_to_purchase=False):
            try:
                with transaction.atomic():
                    purchase = Purchase.objects.create(
                        warehouse=grn.warehouse,
                        bill_no=grn.invoice_no or f"BILL-{grn.grn_no}",
                        vendor=grn.vendor,
                        pur_date=now(),
                        created_by=request.user
                    )
                    for item in grn.items.all():
                        PurchaseItem.objects.create(purchase=purchase, product=item.product, qty=item.qty, price=item.price)
                    grn.converted_to_purchase = True
                    grn.save()
                    count += 1
            except Exception as e:
                self.message_user(request, f"Error: {e}", level=messages.ERROR)
        if count:
            self.message_user(request, f"✅ {count} GRNs converted to purchase.")
    convert_grn_to_purchase.short_description = "🔄 Convert to Purchase"


# ============================================
# PURCHASE ADMIN
# ============================================
class PurchaseAdmin(admin.ModelAdmin):
    list_display = [
        'formatted_pur_date', 'bill_status', 'created_by', 'vendor', 'warehouse',
        'get_vendor_group', 'formatted_previous_balance', 'formatted_total_amount',
        'formatted_paid', 'formatted_outstanding_balance', 'formatted_outstanding_with_previous',
    ]
    search_fields = ('vendor__name','bill_no')
    search_help_text = "Search by Bill No, Vendor Name"
    list_filter = ['pur_date','vendor__group','warehouse',]
    inlines = [PurchaseItemInline]
    list_per_page = 50
    change_form_template = "admin/purchase_barcode.html"  # ✅ ADD THIS LINE
    # ... rest same ...
    change_list_template = "admin/button.html"
    actions = ['generate_html_report', 'generate_vendor_ledger', 'generate_aging_report', 'generate_purchase_pdf']

    def save_model(self, request, obj, form, change):
        if not obj.created_by:  
            obj.created_by = request.user  
        super().save_model(request, obj, form, change)
    
    def formatted_pur_date(self, obj):
        return obj.pur_date.strftime('%d-%m-%Y')
    formatted_pur_date.short_description = 'Purchase Date'

    def formatted_previous_balance(self, obj):
        return f"{obj.previous_balance:,.2f} PKR"
    formatted_previous_balance.short_description = 'Previous Balance'

    def formatted_total_amount(self, obj):
        return f"{obj.total_amount():,.2f} PKR"
    formatted_total_amount.short_description = 'Total Amount'

    def formatted_paid(self, obj):
        return f"{obj.paid:,.2f} PKR"
    formatted_paid.short_description = 'Paid'

    def formatted_outstanding_balance(self, obj):
        return f"{obj.outstanding_balance():,.2f} PKR"
    formatted_outstanding_balance.short_description = 'Outstanding Balance'

    def formatted_outstanding_with_previous(self, obj):
        return f"{obj.outstanding_with_previous():,.2f} PKR"
    formatted_outstanding_with_previous.short_description = 'Outstanding (With Previous)'

    def get_vendor_group(self, obj):
        return obj.vendor.group.name if obj.vendor and obj.vendor.group else None
    get_vendor_group.short_description = 'Vendor Group'

    def generate_aging_report(self, request, queryset):
        today = datetime.now().date()
        aging_data = {
            '30_days': queryset.filter(pur_date__gte=today - timedelta(days=30)).aggregate(Sum('purchaseitem__total_amt'))['purchaseitem__total_amt__sum'] or 0,
            '60_days': queryset.filter(pur_date__gte=today - timedelta(days=60), pur_date__lt=today - timedelta(days=30)).aggregate(Sum('purchaseitem__total_amt'))['purchaseitem__total_amt__sum'] or 0,
            '90_days': queryset.filter(pur_date__lt=today - timedelta(days=60)).aggregate(Sum('purchaseitem__total_amt'))['purchaseitem__total_amt__sum'] or 0,
        }
        context = {'aging_data': aging_data, 'date': datetime.now()}
        html = render_to_string('admin/aging_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="aging_report.html"'
        return response
    generate_aging_report.short_description = "Generate Aging Report"

    def generate_vendor_ledger(self, request, queryset):
        total_outstanding = queryset.aggregate(
            total_outstanding=ExpressionWrapper(
            Sum('purchaseitem__total_amt') - Sum('paid'),
            output_field=DecimalField()
            )
            )['total_outstanding'] or 0
        context = {
        'purchases': queryset,
        'date': datetime.now(),
        'total_outstanding': total_outstanding
        }
        html = render_to_string('admin/vendor_ledger_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="vendor_ledger_report.html"'
        return response
    generate_vendor_ledger.short_description = "Generate Vendor Ledger Report"

    def generate_html_report(self, request, queryset):
        purchases = queryset
        context = {'purchases': purchases, 'date': datetime.now()}
        html = render_to_string('admin/purchase_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="purchase_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'
    
    def generate_purchase_pdf(self, request, queryset):
        """ReportLab use karke Purchase ka PDF report generate karein"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=10)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Purchase Report", title_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Date', 'Bill No', 'Vendor', 'Group', 'Total', 'Paid', 'Outstanding']]
        
        total_amount = Decimal('0.0')
        total_paid = Decimal('0.0')
        total_outstanding = Decimal('0.0')
        
        for purchase in queryset:
            pur_total = purchase.total_amount()
            pur_outstanding = purchase.outstanding_balance()
            table_data.append([
                purchase.pur_date.strftime('%d-%m-%Y'),
                purchase.bill_no or 'Pending',
                purchase.vendor.name,
                purchase.vendor.group.name if purchase.vendor.group else '-',
                f"{pur_total:,.2f}",
                f"{purchase.paid:,.2f}",
                f"{pur_outstanding:,.2f}"
            ])
            total_amount += pur_total
            total_paid += purchase.paid
            total_outstanding += pur_outstanding
        
        table_data.append(['', '', '', 'TOTAL:', f"{total_amount:,.2f}", f"{total_paid:,.2f}", f"{total_outstanding:,.2f}"])
        
        table = Table(table_data, repeatRows=1, colWidths=[1*inch, 1*inch, 1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="purchase_report.pdf"'
        return response
    generate_purchase_pdf.short_description = 'Generate PDF Report'


# ============================================
# PURCHASE ITEM ADMIN
# ============================================
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ('get_pur_date','get_bill_no','vendor','get_vendor_group', 'product','get_category', 'qty', 'formatted_price', 'formatted_total')
    list_per_page = 25
    change_list_template = "admin/button.html"
    search_fields = ('product__name', 'purchase__bill_no', 'purchase__vendor__name')
    search_help_text = "Search by Product Name, Bill Number, or Vendor Name"
    list_filter = ('purchase__pur_date',)
    actions = ['generate_html_report', 'generate_purchase_item_pdf']

    def has_add_permission(self, request):
        return False

    def get_pur_date(self, obj):
        return obj.purchase.pur_date if obj.purchase else 'N/A'
    get_pur_date.short_description = 'Date'

    def get_bill_no(self, obj):
        return obj.purchase.bill_no if obj.purchase and hasattr(obj.purchase, 'bill_no') else 'N/A'
    get_bill_no.short_description = 'Bill No'
    
    def vendor(self, obj):
        return obj.purchase.vendor
    vendor.short_description = 'Vendor'

    def get_vendor_group(self, obj):
        return obj.purchase.vendor.group.name if obj.purchase and obj.purchase.vendor and obj.purchase.vendor.group else None
    get_vendor_group.short_description = 'Vendor Group'

    def get_category(self, obj):
        return obj.product.category.name if obj.product and obj.product.category else 'N/A'
    get_category.short_description = 'Category'

    def formatted_price(self, obj):
        return f"{obj.price:,.2f} PKR"
    formatted_price.short_description = 'Price'

    def formatted_total(self, obj):
        total = Decimal(obj.qty) * obj.price
        return f"{total:,.2f} PKR"
    formatted_total.short_description = 'Total Amount'

    def generate_html_report(self, request, queryset):
        PurchaseItems = queryset
        context = {'PurchaseItems': PurchaseItems, 'date': datetime.now()}
        html = render_to_string('admin/PurchaseItem_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="PurchaseItem_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'
    
    def generate_purchase_item_pdf(self, request, queryset):
        """Generate PDF report for Purchase Items."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=10)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Purchase Items Report", title_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Date', 'Bill No', 'Vendor', 'Product', 'Qty', 'Price', 'Total']]
        
        total_qty = Decimal('0.0')
        total_amount = Decimal('0.0')
        
        for item in queryset:
            qty = Decimal(str(item.qty))
            total = qty * item.price
            table_data.append([
                item.purchase.pur_date.strftime('%d-%m-%Y') if item.purchase else 'N/A',
                item.purchase.bill_no if item.purchase else 'N/A',
                item.purchase.vendor.name if item.purchase else 'N/A',
                item.product.name,
                f"{qty:,.2f}",
                f"{item.price:,.2f}",
                f"{total:,.2f}"
            ])
            total_qty += qty
            total_amount += total
        
        table_data.append(['', '', '', 'TOTAL:', f"{total_qty:,.2f}", '', f"{total_amount:,.2f}"])
        
        table = Table(table_data, repeatRows=1, colWidths=[1*inch, 1*inch, 1.5*inch, 2*inch, 0.8*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="purchase_items_report.pdf"'
        return response
    generate_purchase_item_pdf.short_description = 'Generate PDF Report'


# ============================================
# CUSTOMER GROUP ADMIN
# ============================================
@admin.register(CustomerGroup, site=admin.site)
class CustomerGroupAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    change_list_template = "admin/button.html"
    search_help_text = "Search by Customer Group Name"
    list_display = ['name', 'description', 'total_outstanding_balance_display']
    actions = ['generate_html_report', 'generate_customer_group_pdf']
    
    def total_outstanding_balance_display(self, obj):
        return f'{obj.total_outstanding_balance():,.2f}'
    total_outstanding_balance_display.short_description = 'Total Outstanding Balance'

    def generate_html_report(self, request, queryset):
        CustomerGroups = queryset
        context = {'CustomerGroups': CustomerGroups, 'date': datetime.now()}
        html = render_to_string('admin/CustomerGroup_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="CustomerGroup_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'
    
    def generate_customer_group_pdf(self, request, queryset):
        """Generate PDF report for Customer Groups."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Customer Group Report", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Group Name', 'Description', 'Outstanding Balance']]
        
        for group in queryset:
            table_data.append([
                group.name,
                group.description or '-',
                f"{group.total_outstanding_balance():,.2f}"
            ])
        
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="customer_group_report.pdf"'
        return response
    generate_customer_group_pdf.short_description = 'Generate PDF Report'


# ============================================
# CUSTOMER ADMIN
# ============================================
class CustomerAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    search_help_text = "Search by Customer Name"
    list_display = ('name', 'group', 'address', 'adjusted_outstanding_balance', 'profit_margin')
    list_editable = ('profit_margin',)
    ordering = ('name',)
    change_list_template = "admin/button.html"
    actions = ['generate_html_report', 'generate_customer_pdf']
    readonly_fields = ('adjusted_outstanding_balance',)

    def adjusted_outstanding_balance(self, obj):
        return f'{obj.adjusted_outstanding_balance():,.2f}'
    adjusted_outstanding_balance.short_description = 'Total Outstanding Balance'

    def generate_html_report(self, request, queryset):
        customers = queryset
        context = {'customers': customers, 'date': datetime.now()}
        html = render_to_string('admin/customer_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="customer_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'
    
    def generate_customer_pdf(self, request, queryset):
        """Generate PDF report for Customers."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=10)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Customer Report", title_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Name', 'Group', 'Address', 'Profit Margin %', 'Outstanding Balance']]
        
        total_outstanding = Decimal('0.0')
        for customer in queryset:
            balance = customer.adjusted_outstanding_balance()
            table_data.append([
                customer.name,
                customer.group.name if customer.group else '-',
                (customer.address[:30] + '...') if customer.address and len(customer.address) > 30 else (customer.address or '-'),
                f"{customer.profit_margin:.2f}%",
                f"{balance:,.2f}"
            ])
            total_outstanding += balance
        
        table_data.append(['', '', '', 'TOTAL:', f"{total_outstanding:,.2f}"])
        
        table = Table(table_data, repeatRows=1, colWidths=[1.5*inch, 1.2*inch, 2*inch, 1.2*inch, 1.3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (3, 1), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="customer_report.pdf"'
        return response
    generate_customer_pdf.short_description = 'Generate PDF Report'


# ============================================
# SALE ITEM ADMIN
# ============================================
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('get_sale_date', 'get_bill_no','customer', 'get_customer_group', 'product','get_unit', 'get_category', 'qty', 'formatted_price', 'discount_applied', 'formatted_total', 'discounted_total', 'formatted_profit', 'get_purchase_bill_no')
    list_per_page = 25
    change_list_template = "admin/button.html"
    search_fields = ('product__name', 'sale__bill_no', 'sale__customer__name')
    search_help_text = "Search by Product Name, Bill Number, or Customer Name"
    list_filter = ('sale__sale_date', 'product__category', 'sale__customer')
    actions = ['generate_html_report', 'generate_sale_item_pdf']

    def has_add_permission(self, request):
        return False

    def get_purchase_bill_no(self, obj):
        if not obj.batches_used.exists():
            return "N/A"
        bill_nos = set(
            batch.purchase_item.purchase.bill_no 
            for batch in obj.batches_used.all() 
            if batch.purchase_item and batch.purchase_item.purchase.bill_no
        )
        return ", ".join(bill_nos) if bill_nos else "Waiting for Bill"
    get_purchase_bill_no.short_description = "Purchase Bill No"

    def discount_applied(self, obj):
        total_sale_amount = obj.sale.total_without_discount()
        if total_sale_amount > 0:
            discount_ratio = obj.total_amt / total_sale_amount
            discount = discount_ratio * obj.sale.discount_value
            return round(discount, 2)
        return 0.00

    def discounted_total(self, obj):
        return round(obj.total_amt - self.discount_applied(obj), 2)

    discount_applied.short_description = "Discount Applied"
    discounted_total.short_description = "Discounted Total"

    def customer(self, obj):
        return obj.sale.customer
    customer.short_description = 'Customer'

    def formatted_price(self, obj):
        return f"{obj.price:,.2f} PKR"
    formatted_price.short_description = 'Price'

    def formatted_total(self, obj):
        total = Decimal(obj.qty) * obj.price
        return f"{total:,.2f} PKR"
    formatted_total.short_description = 'Total Amount'

    def formatted_profit(self, obj):
        adjusted_profit = obj.profit - self.discount_applied(obj)
        return f"{adjusted_profit:,.2f} PKR"
    formatted_profit.short_description = 'Profit (Adjusted)'

    def get_sale_date(self, obj):
        return obj.sale.sale_date if obj.sale else 'N/A'
    get_sale_date.short_description = 'Date'

    def get_bill_no(self, obj):
        return obj.sale.bill_no if obj.sale and hasattr(obj.sale, 'bill_no') else 'N/A'
    get_bill_no.short_description = 'Bill No'

    def get_category(self, obj):
        return obj.product.category.name if obj.product and obj.product.category else 'N/A'
    get_category.short_description = 'Category'

    def get_unit(self, obj):
        return obj.product.unit
    get_unit.short_description = 'Unit'

    def generate_html_report(self, request, queryset):
        SaleItems = queryset
        context = {'SaleItems': SaleItems, 'date': datetime.now()}
        html = render_to_string('admin/SaleItem_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="SaleItem_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'

    def view_invoice(self, obj):
        url = reverse('generate_invoice', args=[obj.sale.pk])
        return format_html(f'<a href="{url}" target="_blank">View Invoice</a>')
    view_invoice.short_description = 'Invoice'

    def get_customer_group(self, obj):
        return obj.sale.customer.group.name if obj.sale and obj.sale.customer and obj.sale.customer.group else None
    get_customer_group.short_description = 'Customer Group'
    
    def generate_sale_item_pdf(self, request, queryset):
        """Generate PDF report for Sale Items."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, spaceAfter=10)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Sale Items Report", title_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Date', 'Bill No', 'Customer', 'Product', 'Qty', 'Price', 'Total', 'Profit']]
        
        total_qty = Decimal('0.0')
        total_amount = Decimal('0.0')
        total_profit = Decimal('0.0')
        
        for item in queryset:
            qty = Decimal(str(item.qty))
            total = qty * item.price
            profit = item.profit - item.discount if hasattr(item, 'discount') else item.profit
            table_data.append([
                item.sale.sale_date.strftime('%d-%m-%Y') if item.sale else 'N/A',
                item.sale.bill_no if item.sale else 'N/A',
                item.sale.customer.name if item.sale else 'N/A',
                item.product.name,
                f"{qty:,.2f}",
                f"{item.price:,.2f}",
                f"{total:,.2f}",
                f"{profit:,.2f}"
            ])
            total_qty += qty
            total_amount += total
            total_profit += profit
        
        table_data.append(['', '', '', 'TOTAL:', f"{total_qty:,.2f}", '', f"{total_amount:,.2f}", f"{total_profit:,.2f}"])
        
        table = Table(table_data, repeatRows=1, colWidths=[1*inch, 0.9*inch, 1.3*inch, 1.8*inch, 0.7*inch, 0.9*inch, 0.9*inch, 0.9*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="sale_items_report.pdf"'
        return response
    generate_sale_item_pdf.short_description = 'Generate PDF Report'


# ============================================
# SALE ADMIN
# ============================================
class SaleAdmin(admin.ModelAdmin):
    list_display = ('sale_date','customer', 'warehouse', 'get_customer_group','bill_no','created_by',
                    'formatted_previous_balance', 'formatted_total_without_discount', 'discount_value', 
                    'formatted_total_amount', 'formatted_paid', 'formatted_total_outstanding_with_previous',
                    'formatted_total_profit', 'view_invoice')
    search_fields = ('customer__name','bill_no')
    search_help_text = "Search by Bill No, Customer Name"
    list_filter = ('sale_date','customer__group','warehouse',)
    change_form_template = "admin/barcode_sale.html"
    change_list_template = "admin/button.html"
    inlines = [SaleItemInline]
    actions = ['generate_html_report', 'generate_customer_ledger', 'generate_sales_profit_analysis', 'generate_sale_pdf']
    list_per_page = 50

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['warehouse'].required = True
        if not Warehouse.objects.exists():
            form.base_fields['warehouse'].help_text = "کوئی ویئرہاؤس موجود نہیں۔ براہ کرم پہلے ایک بنائیں۔"
        return form

    def formatted_sale_date(self, obj):
        return obj.sale_date.strftime('%d-%m-%y')
    formatted_sale_date.short_description = 'Sale Date'

    def formatted_total_without_discount(self, obj):
        return f"{obj.total_without_discount():,.2f} PKR"
    formatted_total_without_discount.short_description = 'Total_without_Discount'

    def formatted_total_amount(self, obj):
        return f"{obj.total_amount():,.2f} PKR"
    formatted_total_amount.short_description = 'Total Amount'

    def formatted_total_profit(self, obj):
        return f"{obj.total_profit():,.2f} PKR"
    formatted_total_profit.short_description = 'Total Profit'

    def formatted_paid(self, obj):
        return f"{obj.paid:,.2f} PKR"
    formatted_paid.short_description = 'Paid'

    def formatted_previous_balance(self, obj):
        return f"{obj.previous_balance:,.2f} PKR"
    formatted_previous_balance.short_description = 'Previous Balance'

    def formatted_total_outstanding_with_previous(self, obj):
        return f"{obj.total_outstanding_with_previous:,.2f} PKR"
    formatted_total_outstanding_with_previous.short_description = 'Total_Outstanding_With_Previous'

    def generate_sales_profit_analysis(self, request, queryset):
        profit_data = queryset.aggregate(
            total_sales=Sum('saleitem__total_amt'),
            total_profit=Sum('saleitem__profit')
        )
        context = {'profit_data': profit_data, 'date': datetime.now()}
        html = render_to_string('admin/sales_profit_analysis.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="sales_profit_analysis.html"'
        return response
    generate_sales_profit_analysis.short_description = "Generate Sales & Profit Analysis"

    def generate_html_report(self, request, queryset):
        sales = queryset
        context = {'sales': sales, 'date': datetime.now()}
        html = render_to_string('admin/sale_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="sale_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'

    def generate_customer_ledger(self, request, queryset):
        total_outstanding = queryset.aggregate(
            total_outstanding=ExpressionWrapper(
            Sum('saleitem__total_amt') - Sum('paid'),
            output_field=DecimalField()
            )
            )['total_outstanding'] or 0
        context = {'sales': queryset, 'date': datetime.now(), 'total_outstanding': total_outstanding}
        html = render_to_string('admin/customer_ledger_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="customer_ledger_report.html"'
        return response
    generate_customer_ledger.short_description = "Generate Customer Ledger Report"

    def view_invoice(self, obj):
        url = reverse('admin:generate_invoice', args=[obj.pk])
        return format_html(f'<a href="{url}" target="_blank">View Invoice</a>')
    view_invoice.short_description = 'Invoice'

    def get_customer_group(self, obj):
        return obj.customer.group.name if obj.customer and obj.customer.group else None
    get_customer_group.short_description = 'Customer Group'

    def save_model(self, request, obj, form, change):
        if not obj.created_by:  
            obj.created_by = request.user 
        if not obj.warehouse:
            default_warehouse = Warehouse.objects.first()
            if default_warehouse:
                obj.warehouse = default_warehouse
            else:
                self.message_user(request, "کوئی ویئرہاؤس موجود نہیں۔ براہ کرم پہلے ایک بنائیں۔", level=messages.ERROR)
                return
        super().save_model(request, obj, form, change)
    
    def generate_sale_pdf(self, request, queryset):
        """Sale ka PDF report generate karein"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=10)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Sale Report", title_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Date', 'Bill No', 'Customer', 'Group', 'Total', 'Discount', 'Paid', 'Profit']]
        
        total_amount = Decimal('0.0')
        total_discount = Decimal('0.0')
        total_paid = Decimal('0.0')
        total_profit = Decimal('0.0')
        
        for sale in queryset:
            total_amt = sale.total_without_discount()
            table_data.append([
                sale.sale_date.strftime('%d-%m-%Y'),
                sale.bill_no,
                sale.customer.name,
                sale.customer.group.name if sale.customer.group else '-',
                f"{total_amt:,.2f}",
                f"{sale.discount_value:,.2f}",
                f"{sale.paid:,.2f}",
                f"{sale.total_profit():,.2f}"
            ])
            total_amount += total_amt
            total_discount += sale.discount_value
            total_paid += sale.paid
            total_profit += sale.total_profit()
        
        table_data.append(['', '', '', 'TOTAL:', f"{total_amount:,.2f}", f"{total_discount:,.2f}", f"{total_paid:,.2f}", f"{total_profit:,.2f}"])
        
        table = Table(table_data, repeatRows=1, colWidths=[1*inch, 1*inch, 1.5*inch, 1*inch, 1*inch, 0.9*inch, 0.9*inch, 0.9*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="sale_report.pdf"'
        return response
    generate_sale_pdf.short_description = 'Generate PDF Report'


# ============================================
# INVENTORY ADMIN
# ============================================
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'get_description', 'get_unit', 'get_location', 'get_used', 'get_brand', 
                    'get_category', 'get_types', 'warehouse', 'stock', 'stock_value_display', 'low_stock_alert')
    ordering = ('product',)
    change_list_template = "admin/button.html"
    actions = ['send_bulk_low_stock_alerts', 'generate_html_report', 'generate_inventory_pdf']
    search_fields = (
        'product__name', 'warehouse__name', 'product__unit__name', 'product__location__name',
        'product__used', 'product__brand__name', 'product__category__name', 'product__types__name',
        'product__description',
    )
    search_help_text = 'Search by Product Name, Warehouse, Unit, Location, Used, Brand, Category, Type'

    def has_add_permission(self, request):
        return False

    def send_bulk_low_stock_alerts(self, request, queryset):
        Inventory.send_bulk_low_stock_alert()
        self.message_user(request, "Low stock alert email sent successfully.")
    send_bulk_low_stock_alerts.short_description = "Send Low Stock Alert"
    
    def stock_value_display(self, obj):
        stock_value = obj.stock_value()
        return f"{stock_value:,.2f} PKR"
    stock_value_display.short_description = 'Stock Value'

    def low_stock_alert(self, obj):
        if obj.check_low_stock():
            return format_html('<span style="color: red;">Low Stock</span>')
        return "OK"
    low_stock_alert.short_description = "Stock Alert"

    def get_description(self, obj):
        return obj.product.description if obj.product.description else "N/A"
    get_description.short_description = "Description"
    
    def get_unit(self, obj):
        return obj.product.unit.name if obj.product.unit else "N/A"
    get_unit.short_description = "Unit"

    def get_location(self, obj):
        return obj.product.location.name if obj.product.location else "N/A"
    get_location.short_description = "Location"

    def get_used(self, obj):
        return obj.product.used if obj.product.used else "N/A"
    get_used.short_description = "Used"

    def get_brand(self, obj):
        return obj.product.brand.name if obj.product.brand else "N/A"
    get_brand.short_description = "Brand"

    def get_category(self, obj):
        return obj.product.category.name if obj.product.category else "N/A"
    get_category.short_description = "Category"

    def get_types(self, obj):
        return obj.product.types.name if obj.product.types else "N/A"
    get_types.short_description = "Type"

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        qs = self.get_queryset(request)
        total_stock_value = sum(item.stock_value() for item in qs) or Decimal('0.0')
        summary_data = {'total_stock_value': f"{total_stock_value:,.2f} PKR"}
        if hasattr(response, 'context_data'):
            response.context_data['summary_data'] = summary_data
        return response

    def generate_html_report(self, request, queryset):
        inventorys = queryset
        context = {'inventorys': inventorys, 'date': datetime.now()}
        html = render_to_string('admin/inventory_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="inventory_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'
    
    def generate_inventory_pdf(self, request, queryset):
        """Inventory stock ka PDF report"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=10)
        story.append(Paragraph(company_name, title_style))
        story.append(Paragraph("Inventory Stock Report", title_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        table_data = [['Product', 'Warehouse', 'Stock', 'Price', 'Stock Value', 'Status']]
        
        total_value = Decimal('0.0')
        
        for idx, inv in enumerate(queryset, start=1):
            stock_value = inv.stock_value()
            status = "LOW STOCK!" if inv.check_low_stock() else "OK"
            table_data.append([
                inv.product.name[:30],
                inv.warehouse.name,
                f"{inv.stock:,.2f}",
                f"{inv.product.price:,.2f}",
                f"{stock_value:,.2f}",
                status
            ])
            total_value += Decimal(str(stock_value))
        
        table_data.append(['', '', '', 'TOTAL VALUE:', f"{total_value:,.2f}", ''])
        
        table = Table(table_data, repeatRows=1, colWidths=[2*inch, 1.2*inch, 0.8*inch, 1*inch, 1.2*inch, 1*inch])
        
        # Pehle base style apply karein
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]
        
        # Low stock rows ko highlight karein
        row_idx = 1
        for inv in queryset:
            if inv.check_low_stock():
                table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightpink))
                table_style.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.red))
            row_idx += 1
        
        table.setStyle(TableStyle(table_style))
        story.append(table)
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="inventory_report.pdf"'
        return response
    generate_inventory_pdf.short_description = 'Generate PDF Report'


# ============================================
# STOCK BATCH ADMIN
# ============================================
class StockBatchAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'qty', 'price', 'remaining_qty', 'batch_value_display','get_purchase_bill_no','get_sale_bill_no')
    search_fields = (
        'product__name', 'purchase_item__purchase__bill_no', 
        'sale_items__sale__bill_no', 'warehouse__name',
    )
    search_help_text = "Search by Product Name, Warehouse, Purchase Bill No, or Sale Bill No"
    list_filter = ('warehouse',)
    change_list_template = "admin/button.html"

    def has_add_permission(self, request):
        return False

    def batch_value_display(self, obj):
        return f"{Decimal(obj.remaining_qty) * obj.price:,.2f} PKR"
    batch_value_display.short_description = 'Batch Value (PKR)'

    def get_purchase_bill_no(self, obj):
        if obj.purchase_item and obj.purchase_item.purchase:
            return obj.purchase_item.purchase.bill_no if obj.purchase_item.purchase.bill_no else "Waiting for Bill"
        return "N/A"
    get_purchase_bill_no.short_description = "Purchase Bill No"

    def get_sale_bill_no(self, obj):
        if not obj.sale_items.exists():
            return "Not Sold Yet"
        bill_nos = set(
            sale_item.sale.bill_no 
            for sale_item in obj.sale_items.all() 
            if sale_item.sale and sale_item.sale.bill_no
        )
        return ", ".join(bill_nos) if bill_nos else "N/A"
    get_sale_bill_no.short_description = "Sale Bill No"


# ============================================
# MONTHLY CLOSING ADMIN
# ============================================
class MonthlyClosingAdmin(admin.ModelAdmin):
    list_display = ['month', 'previous_balance_display','total_purchase_balance_display',
                    'total_sale_balance_display', 'closing_balance_display',
                    'total_sale_profit_display', 'total_purchase_return_display',
                    'total_sale_return_display', 'net_profit_margin_display', 
                    'return_on_investment_display', 'locked']
    actions = ['lock_month', 'unlock_month', 'generate_html_report', 'generate_pnl', 
               'generate_cash_flow', 'generate_saving', 'generate_closing_pdf']
    ordering = ('-month',)
    change_list_template = "admin/button.html"

    def lock_month(self, request, queryset):
        queryset.update(locked=True)
        self.message_user(request, "Selected months have been locked.")
    lock_month.short_description = "Lock selected months"

    def unlock_month(self, request, queryset):
        queryset.update(locked=False)
        self.message_user(request, "Selected months have been unlocked.")
    unlock_month.short_description = "Unlock selected months"

    def total_purchase_return_display(self, obj):
        return f'{obj.total_purchase_return():,.2f}'
    total_purchase_return_display.short_description = 'Purchase Returns'

    def total_sale_return_display(self, obj):
        return f'{obj.total_sale_return():,.2f}'
    total_sale_return_display.short_description = 'Sale Returns'

    def total_purchase_balance_display(self, obj):
        return f'{obj.total_purchase_balance():,.2f}'
    total_purchase_balance_display.short_description = 'Total Purchase'

    def total_sale_profit_display(self, obj):
        return f'{obj.total_sale_profit():,.2f}'
    total_sale_profit_display.short_description = 'Total Profit'

    def total_sale_balance_display(self, obj):
        return f'{obj.total_sale_balance():,.2f}'
    total_sale_balance_display.short_description = 'Total Sale (COGS)'

    def closing_balance_display(self, obj):
        return f'{obj.closing_balance():,.2f}'
    closing_balance_display.short_description = 'Closing Balance'
    
    def previous_balance_display(self, obj):
        return f"{obj.get_previous_month_closing():,.2f}"
    previous_balance_display.short_description = "Previous Balance"

    def net_profit_margin_display(self, obj):
        return f"{obj.net_profit_margin():.2f}%"
    net_profit_margin_display.short_description = "Net Profit Margin"

    def return_on_investment_display(self, obj):
        return f"{obj.return_on_investment():.2f}%"
    return_on_investment_display.short_description = "ROI"

    def generate_pnl(self, request, queryset):
        for closing in queryset:
            income = closing.total_sale_profit()
            expenses = (Expense.objects.filter(date__month=closing.month.month).aggregate(Sum('amount'))['amount__sum'] or 0)
            profit = income - expenses
            context = {'income': income, 'expenses': expenses, 'profit': profit, 'month': closing.month}
            html = render_to_string('admin/pnl_report.html', context)
            response = HttpResponse(html, content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="pnl_{closing.month}.html"'
            return response
    generate_pnl.short_description = "Generate Profit & Loss Statement"

    def generate_saving(self, request, queryset):
        for closing in queryset:
            savings = (Saving.objects.filter(date__month=closing.month.month).aggregate(Sum('amount'))['amount__sum'] or 0)
            context = {'savings': savings, 'month': closing.month}
            html = render_to_string('admin/saving_report.html', context)
            response = HttpResponse(html, content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="saving_{closing.month}.html"'
            return response
    generate_saving.short_description = "Generate Saving"

    def generate_cash_flow(self, request, queryset):
        for closing in queryset:
            cash_in = Sale.objects.filter(sale_date__month=closing.month.month).aggregate(Sum('paid'))['paid__sum'] or 0
            cash_out = Purchase.objects.filter(pur_date__month=closing.month.month).aggregate(Sum('paid'))['paid__sum'] or 0
            net_cash = cash_in - cash_out
            context = {'cash_in': cash_in, 'cash_out': cash_out, 'net_cash': net_cash, 'month': closing.month}
            html = render_to_string('admin/cash_flow_report.html', context)
            response = HttpResponse(html, content_type='text/html')
            response['Content-Disposition'] = f'attachment; filename="cash_flow_{closing.month}.html"'
            return response
    generate_cash_flow.short_description = "Generate Cash Flow Statement"

    def generate_html_report(self, request, queryset):
        MonthlyClosings = queryset
        context = {'MonthlyClosings': MonthlyClosings, 'date': datetime.now()}
        html = render_to_string('admin/MonthlyClosing_report.html', context)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = 'attachment; filename="MonthlyClosing_report.html"'
        return response
    generate_html_report.short_description = 'Generate HTML Report'
    
    def generate_closing_pdf(self, request, queryset):
        """Monthly closing ka PDF report"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=TA_CENTER, spaceAfter=10)
        
        for closing in queryset:
            story.append(Paragraph(company_name, title_style))
            story.append(Paragraph(f"Monthly Closing Report - {closing.month.strftime('%B %Y')}", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            data = [
                ['Description', 'Amount (PKR)'],
                ['Previous Balance', f"{closing.previous_balance:,.2f}"],
                ['Total Purchases', f"{closing.total_purchase_balance():,.2f}"],
                ['Purchase Returns', f"{closing.total_purchase_return():,.2f}"],
                ['Total Sales (COGS)', f"{closing.total_sale_balance():,.2f}"],
                ['Sale Returns', f"{closing.total_sale_return():,.2f}"],
                ['Total Profit', f"{closing.total_sale_profit():,.2f}"],
                ['Closing Balance', f"{closing.closing_balance():,.2f}"],
                ['Net Profit Margin', f"{closing.net_profit_margin():.2f}%"],
                ['Return on Investment (ROI)', f"{closing.return_on_investment():.2f}%"],
            ]
            
            table = Table(data, colWidths=[3*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTNAME', (0, -2), (0, -1), 'Helvetica-Bold'),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.5*inch))
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="monthly_closing.pdf"'
        return response
    generate_closing_pdf.short_description = 'Generate PDF Report'


# ============================================
# PURCHASE RETURN ADMIN
# ============================================
class PurchaseRetrnAdmin(admin.ModelAdmin):
    inlines = [PurchaseRetrnItemInline]
    list_display = ('purchase_return_date','bill_no', 'purchase', 'vendor', 'created_by', 'return_reason')
    change_list_template = "admin/button.html"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:  
            obj.created_by = request.user  
        super().save_model(request, obj, form, change)


class PurchaseRetrnItemAdmin(admin.ModelAdmin):
    list_display = ('purchase_return', 'product', 'qty', 'price', 'total_amt')
    change_list_template = "admin/button.html"

    def has_add_permission(self, request):
        return False


# ============================================
# SALE RETURN ADMIN
# ============================================
class SaleRetrnAdmin(admin.ModelAdmin):
    inlines = [SaleRetrnItemInline]
    list_display = ('sale_return_date','bill_no', 'sale', 'customer', 'created_by', 'return_reason')
    change_list_template = "admin/button.html"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:  
            obj.created_by = request.user  
        super().save_model(request, obj, form, change)


class SaleRetrnItemAdmin(admin.ModelAdmin):
    list_display = ('sale_return', 'product', 'qty', 'price', 'total_amt')
    change_list_template = "admin/button.html"

    def has_add_permission(self, request):
        return False


# ============================================
# STOCK ADJUSTMENT ADMIN
# ============================================
@admin.register(StockAdjustmentItem, site=admin.site)
class StockAdjustmentItemAdmin(admin.ModelAdmin):
    list_display = ('adjustment', 'product', 'qty', 'price', 'total_value')
    search_fields = ('product__name',)
    readonly_fields = ('total_value',)
    change_list_template = "admin/button.html"

    def has_add_permission(self, request):
        return False


class StockAdjustmentItemInline(admin.TabularInline):
    model = StockAdjustmentItem
    extra = 1
    fields = ('product', 'qty', 'price', 'total_value')
    readonly_fields = ('total_value',)


@admin.register(StockAdjustment, site=admin.site)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('adjustment_type', 'reason', 'adjustment_date', 'created_by')
    change_list_template = "admin/button.html"
    search_fields = ('reason', 'created_by__username')
    inlines = [StockAdjustmentItemInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ============================================
# LOG ENTRY ADMIN
# ============================================
class ActionFlagFilter(SimpleListFilter):
    title = "Action Type"
    parameter_name = "action_flag"

    def lookups(self, request, model_admin):
        return [(1, "Added"), (2, "Changed"), (3, "Deleted")]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(action_flag=self.value())


class ContentTypeFilter(SimpleListFilter):
    title = "Content Type"
    parameter_name = "content_type"

    def lookups(self, request, model_admin):
        content_types = set(model_admin.get_queryset(request).values_list("content_type__id", "content_type__model"))
        return [(ct_id, model.replace("_", " ").title()) for ct_id, model in content_types]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(content_type__id=self.value())


class LogEntryAdmin(admin.ModelAdmin):
    change_list_template = "admin/button.html"
    list_display = ['action_time', 'user', 'content_type_display', 'action']
    list_filter = ['action_time', 'user', ActionFlagFilter, ContentTypeFilter]

    @admin.display(description="Action", ordering="action_flag")
    def action(self, obj):
        if obj.action_flag == 1:
            return format_html('<span style="color: blue; font-weight: bold;">Added</span>')
        elif obj.action_flag == 2:
            return format_html('<span style="color: orange; font-weight: bold;">Changed</span>')
        elif obj.action_flag == 3:
            return format_html('<span style="color: red; font-weight: bold;">Deleted</span>')
        return "Unknown"

    @admin.display(description="Content Type")
    def content_type_display(self, obj):
        return obj.content_type.model_class()._meta.verbose_name.title()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True 


# ============================================
# LICENSE ADMIN
# ============================================
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('key', 'expiry_date', 'created_at', 'is_valid')
    readonly_fields = ('created_at',)
    change_list_template = "admin/button.html"

    def is_valid(self, obj):
        return "✔ Active" if obj.is_valid() else "❌ Expired"
    is_valid.short_description = "Status"


# ============================================
# EXPENSE, SAVING, DEBT ADMIN
# ============================================
@admin.register(Expense, site=admin.site)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'date', 'category')
    list_filter = ('category', 'date')
    search_fields = ('description',)


@admin.register(Saving, site=admin.site)
class SavingAdmin(admin.ModelAdmin):
    list_display = ('description', 'amount', 'date', 'category')
    list_filter = ('category', 'date')
    search_fields = ('description',)


@admin.register(Debt, site=admin.site)
class DebtAdmin(admin.ModelAdmin):
    list_display = ('lender', 'amount', 'interest_rate', 'start_date', 'due_date')
    list_filter = ('start_date', 'due_date')
    search_fields = ('lender',)


# ============================================
# TRAINING ADMIN
# ============================================
class TrainingStepInline(admin.TabularInline):
    model = TrainingStep
    extra = 1
    fields = ['step_number', 'description', 'screenshot_preview']
    readonly_fields = ['screenshot_preview']

    def screenshot_preview(self, obj):
        if obj.screenshot:
            return format_html('<img src="{}" width="100" />', obj.screenshot.url)
        return "No Image"
    screenshot_preview.short_description = "Screenshot"


class TrainingTopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'order']
    ordering = ['category', 'order']
    search_fields = ['title']
    inlines = [TrainingStepInline]

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class TrainingStepAdmin(admin.ModelAdmin):
    list_display = ['topic_name', 'step_number_display', 'short_description', 'has_screenshot']
    ordering = ['topic', 'step_number']
    list_display_links = None

    def topic_name(self, obj):
        return obj.topic.title
    topic_name.short_description = "Topic"
    topic_name.admin_order_field = "topic"

    def step_number_display(self, obj):
        return obj.step_number
    step_number_display.short_description = "Step #"
    step_number_display.admin_order_field = "step_number"

    def short_description(self, obj):
        return obj.description[:60] + "..." if len(obj.description) > 60 else obj.description
    short_description.short_description = "Description"

    def has_screenshot(self, obj):
        return "✅" if obj.screenshot else "❌"
    has_screenshot.short_description = "Screenshot"

    def has_add_permission(self, request):
        return False


# ============================================
# COMPANY INFO ADMIN
# ============================================
class CompanyInfoAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_number', 'email', 'website', 'updated_at']
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        if CompanyInfo.objects.exists():
            return False
        return True
        

class StockAuditItemInline(admin.TabularInline):
    model = StockAuditItem
    fields = ('product', 'system_qty', 'physical_qty', 'variance_display', 'variance_value_display', 'unit', 'adjusted', 'notes')
    readonly_fields = ('system_qty', 'variance_display', 'variance_value_display', 'unit')
    extra = 0
    
    def variance_display(self, obj):
        if obj and obj.pk:
            return obj.variance_display()
        return "-"
    variance_display.short_description = "Variance"
    
    def variance_value_display(self, obj):
        if obj and obj.pk:
            return obj.variance_value_display()
        return "-"
    variance_value_display.short_description = "Variance Value"
    
@admin.register(StockAudit, site=admin.site)
class StockAuditAdmin(admin.ModelAdmin):
    list_display = ('audit_no', 'audit_date', 'warehouse', 'status', 'total_items_display', 
                    'variance_items_count', 'total_variance_value_display', 'print_audit')
    list_filter = ('status', 'audit_date', 'warehouse')
    search_fields = ('audit_no', 'warehouse__name')
    inlines = [StockAuditItemInline]
    change_list_template = "admin/button.html"
    actions = ['generate_audit_sheet', 'mark_completed', 'adjust_stock', 'generate_audit_pdf']
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('audit_no', 'warehouse', 'audit_date', 'status')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )
    
    readonly_fields = ('audit_no', 'total_variance_value')
    
    def total_items_display(self, obj):
        return obj.total_items()
    total_items_display.short_description = "Items"
    
    def variance_items_count(self, obj):
        count = obj.items.filter(physical_qty__isnull=False).filter(
            models.Q(variance__gt=0) | models.Q(variance__lt=0)
        ).count()
        if count > 0:
            return format_html('<span style="color: red;">⚠ {} variance(s)</span>', count)
        return "0"
    variance_items_count.short_description = "Variances"
    
    def total_variance_value_display(self, obj):
        val = obj.total_variance_value
        if val < 0:
            return format_html('<span style="color: red;">Rs. ({})</span>', str(round(abs(val), 2)))
        elif val > 0:
            return format_html('<span style="color: green;">Rs. {}</span>', str(round(val, 2)))
        return "Rs. 0.00"
    total_variance_value_display.short_description = "Net Variance"
    
    def print_audit(self, obj):
        url = reverse('admin:generate_audit_pdf', args=[obj.pk])
        return format_html('<a href="{}" target="_blank">📄 Print</a>', url)
    print_audit.short_description = "Print"
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if instance.pk is None:
                inventory = Inventory.objects.filter(
                    product=instance.product, 
                    warehouse=formset.instance.warehouse
                ).first()
                instance.system_qty = inventory.stock if inventory else 0
            instance.save()
        formset.save_m2m()
    
    def generate_audit_sheet(self, request, queryset):
        """Auto-populate audit with all warehouse products"""
        for audit in queryset.filter(status='draft'):
            inventories = Inventory.objects.filter(warehouse=audit.warehouse)
            for inv in inventories:
                if not StockAuditItem.objects.filter(audit=audit, product=inv.product).exists():
                    StockAuditItem.objects.create(
                        audit=audit,
                        product=inv.product,
                        system_qty=inv.stock,
                        unit=inv.product.unit.name if inv.product.unit else ''
                    )
            audit.status = 'in_progress'
            audit.save()
        self.message_user(request, f"✅ Audit sheets generated with products.")
    generate_audit_sheet.short_description = "📋 Generate Audit Sheet (Add All Products)"
    
    def mark_completed(self, request, queryset):
        """Mark audit as completed and calculate total variance"""
        for audit in queryset.filter(status='in_progress'):
            total_var = audit.items.aggregate(t=Sum('variance_value'))['t'] or Decimal('0.0')
            audit.total_variance_value = total_var
            audit.status = 'completed'
            audit.save()
        self.message_user(request, f"✅ Audits marked as completed.")
    mark_completed.short_description = "✅ Mark as Completed"
    
    def adjust_stock(self, request, queryset):
        """Adjust stock based on audit variance"""
        count = 0
        for audit in queryset.filter(status='completed'):
            with transaction.atomic():
                for item in audit.items.filter(physical_qty__isnull=False, adjusted=False):
                    if item.variance != 0:
                        adj_type = 'increase' if item.variance > 0 else 'decrease'
                        adjustment = StockAdjustment.objects.create(
                            adjustment_type=adj_type,
                            reason=f"Audit {audit.audit_no}: Variance for {item.product.name}",
                            created_by=request.user
                        )
                        StockAdjustmentItem.objects.create(
                            adjustment=adjustment,
                            product=item.product,
                            qty=abs(item.variance),
                            price=item.price
                        )
                        item.adjusted = True
                        item.save()
                        count += 1
        if count:
            self.message_user(request, f"✅ {count} variances adjusted. Stock updated!")
        else:
            self.message_user(request, "No variances to adjust.")
    adjust_stock.short_description = "🔄 Adjust Stock (Fix Variances)"
    
    def generate_audit_pdf(self, request, queryset):
        """Generate PDF for audit with brackets for negative values"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.3*inch, bottomMargin=0.5*inch)
        styles = getSampleStyleSheet()
        story = []
        
        company = CompanyInfo.objects.first()
        company_name = company.name if company else "Company Name"
        
        for audit in queryset:
            title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER)
            story.append(Paragraph(company_name, title_style))
            story.append(Paragraph("<b>STOCK AUDIT REPORT</b>", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            details = [
                [Paragraph(f"<b>Audit No:</b> {audit.audit_no}"), 
                 Paragraph(f"<b>Date:</b> {audit.audit_date.strftime('%d-%m-%Y')}")],
                [Paragraph(f"<b>Warehouse:</b> {audit.warehouse.name}"), 
                 Paragraph(f"<b>Status:</b> {audit.get_status_display()}")],
            ]
            story.append(Table(details, colWidths=[3.5*inch, 3.5*inch]))
            story.append(Spacer(1, 0.2*inch))
            
            table_data = [['Product', 'System Qty', 'Physical Qty', 'Variance', 'Unit', 'Value']]
            total_var_value = Decimal('0.0')
            
            for item in audit.items.all():
                # Physical qty
                if item.physical_qty is not None:
                    physical = f"{item.physical_qty:,.0f}"
                else:
                    physical = '?'
                
                # ✅ Variance quantity with brackets for negative
                if item.physical_qty is not None:
                    if item.variance < 0:
                        var_str = f"({abs(item.variance):,.0f})"
                    elif item.variance > 0:
                        var_str = f"{item.variance:+,.0f}"
                    else:
                        var_str = "0"
                else:
                    var_str = '-'
                
                # ✅ Variance value with brackets for negative
                if item.physical_qty is not None:
                    if item.variance_value < 0:
                        val_str = f"Rs. ({abs(item.variance_value):,.2f})"
                    elif item.variance_value > 0:
                        val_str = f"Rs. {item.variance_value:,.2f}"
                    else:
                        val_str = "Rs. 0.00"
                else:
                    val_str = '-'
                
                table_data.append([
                    item.product.name[:25],
                    f"{item.system_qty:,.0f}",
                    physical,
                    var_str,
                    item.unit or '-',
                    val_str
                ])
                total_var_value += item.variance_value
            
            # ✅ Total row with brackets for negative
            if total_var_value < 0:
                total_str = f"Rs. ({abs(total_var_value):,.2f})"
            elif total_var_value > 0:
                total_str = f"Rs. {total_var_value:,.2f}"
            else:
                total_str = "Rs. 0.00"
            
            table_data.append(['', '', '', '', 'NET:', total_str])
            
            items_table = Table(table_data, repeatRows=1)
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            story.append(items_table)
            
            story.append(Spacer(1, 0.5*inch))
            sign = [
                [Paragraph("<b>Counted by:</b> _________"), Paragraph("<b>Verified by:</b> _________")],
                [Paragraph("Date: _________"), Paragraph("Date: _________")],
            ]
            story.append(Table(sign, colWidths=[3.5*inch, 3.5*inch]))
            story.append(Paragraph("<br/><br/>", styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return HttpResponse(buffer, content_type='application/pdf')
    generate_audit_pdf.short_description = "📄 Generate Audit PDF"


# ============================================
# REGISTER ALL MODELS
# ============================================
admin.site.register(CompanyInfo, CompanyInfoAdmin)
admin.site.register(Brand)
admin.site.register(Category)
admin.site.register(Types)
admin.site.register(Location)
admin.site.register(Unit)
admin.site.register(Purchase, PurchaseAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Sale, SaleAdmin)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(StockBatch, StockBatchAdmin)
admin.site.register(PurchaseItem, PurchaseItemAdmin)
admin.site.register(SaleItem, SaleItemAdmin)
admin.site.register(MonthlyClosing, MonthlyClosingAdmin)
admin.site.register(PurchaseRetrn, PurchaseRetrnAdmin)
admin.site.register(PurchaseRetrnItem, PurchaseRetrnItemAdmin)
admin.site.register(SaleRetrn, SaleRetrnAdmin)
admin.site.register(SaleRetrnItem, SaleRetrnItemAdmin)
admin.site.register(LogEntry, LogEntryAdmin)
admin.site.register(License, LicenseAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(TrainingStep, TrainingStepAdmin)
admin.site.register(TrainingTopic, TrainingTopicAdmin)