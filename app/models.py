from django.db import models, transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.db.models import Sum,F
from django.db.models import Min
from django.contrib.auth.models import User
import logging
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
import hashlib

logger = logging.getLogger(__name__)



class CompanyInfo(models.Model):
    name = models.CharField("Company Name", max_length=255)
    tagline = models.CharField("Tagline", max_length=255, blank=True, null=True)
    address = models.TextField("Address")
    contact_number = models.CharField("Phone", max_length=50)
    email = models.EmailField("Email")
    website = models.URLField("Website", blank=True, null=True)
    logo = models.ImageField("Company Logo", upload_to="company_logo/", blank=True, null=True)
    footer_note = models.CharField("Footer Note (for reports)", max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Company Information"
        verbose_name_plural = "Company Information"


class TrainingTopic(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, choices=[
        ('product', 'Product Management'),
        ('purchase', 'Purchases'),
        ('sale', 'Sales'),
        ('warehouse', 'Warehouse Management'),
        ('report', 'Reporting'),
        ('backup', 'Backup & Restore'),
        ('other', 'Other')
    ])
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']
        verbose_name_plural = "📘 Training Topics"

    def __str__(self):
        return self.title


class TrainingStep(models.Model):
    topic = models.ForeignKey(TrainingTopic, on_delete=models.CASCADE, related_name="steps")
    step_number = models.PositiveIntegerField()
    description = models.TextField(help_text="Explain what the user should do in this step.")
    screenshot = models.ImageField(upload_to="training_screenshots/", null=True, blank=True)

    class Meta:
        ordering = ['step_number']
        verbose_name_plural = "📗 Training Steps"

    def __str__(self):
        return f"{self.topic.title} - Step {self.step_number}"

class Expense(models.Model):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateTimeField(default=now)
    category = models.CharField(max_length=100, choices=[
        ('rent', 'Rent'),
        ('salary', 'Salary'),
        ('utilities', 'Utilities'),
        ('other', 'Other'),
    ], default='other')

    def __str__(self):
        return f"{self.description} - {self.amount}"

    class Meta:
        verbose_name_plural = "10. Expenses"

class Saving(models.Model):
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateTimeField(default=now)
    category = models.CharField(max_length=100, choices=[
        ('utilities', 'Utilities'),
        ('other', 'Other'),
    ], default='other')

    def __str__(self):
        return f"{self.description} - {self.amount}"

    class Meta:
        verbose_name_plural = "10.2 Savings"

# New model for debts
class Debt(models.Model):
    lender = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    start_date = models.DateField(default=now)
    due_date = models.DateField()

    def __str__(self):
        return f"{self.lender} - {self.amount}"

    class Meta:
        verbose_name_plural = "10.1. Debts"

# Brand model to store brand details
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = '1.1 Product Brands'

    def __str__(self):
        return self.name

# Category model to store category details
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = '1.2 Product Category'

    def __str__(self):
        return self.name

class Types(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = '1.3 Product Type'

    def __str__(self):
        return self.name

class Location(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = '1.4 Product Location'

    def __str__(self):
        return self.name

class Unit(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name_plural = '1.5 Product Unit'

    def __str__(self):
        return self.name

# Updated Product 
class Product(models.Model):
    serial_no = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name=_("Serial Number"))
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name=_("Barcode"))
    use_custom_barcode = models.BooleanField(default=False, verbose_name=_("Use Custom/Supplier Barcode"), help_text="Check this to manually enter supplier barcode instead of auto-generating")
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    used = models.TextField(null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    types = models.ForeignKey(Types, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.0'), editable=False)
    low_stock_threshold = models.FloatField(default=10.0, help_text="Set minimum stock level for alerts.")
    
    class Meta:
        verbose_name_plural = '1. Product Name'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['barcode']),
        ]

    def __str__(self):
        serial = self.serial_no if self.serial_no else "N/A"
        return f"{self.name} (Barcode: {self.barcode or 'N/A'})"
    
    def save(self, *args, **kwargs):
        # ✅ Agar use_custom_barcode True hai ya barcode already set hai to auto-generate NA karein
        #if not self.use_custom_barcode and not self.barcode:
            #self.barcode = self.generate_barcode()
        pass
        super().save(*args, **kwargs)
    
    def generate_barcode(self):
        """Generate unique EAN-13 barcode"""
        import random
        prefix = "200"  # Company prefix (change as needed)
        while True:
            random_digits = ''.join([str(random.randint(0, 9)) for _ in range(9)])
            barcode = prefix + random_digits
            check_digit = self.calculate_ean13_check_digit(barcode)
            full_barcode = barcode + str(check_digit)
            if not Product.objects.filter(barcode=full_barcode).exists():
                return full_barcode
    
    def calculate_ean13_check_digit(self, barcode_12):
        """Calculate EAN-13 check digit"""
        if len(barcode_12) != 12:
            return 0
        odd_sum = sum(int(barcode_12[i]) for i in range(0, 12, 2))
        even_sum = sum(int(barcode_12[i]) for i in range(1, 12, 2))
        total = odd_sum + (even_sum * 3)
        check_digit = (10 - (total % 10)) % 10
        return check_digit

class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "6. Warehouses"
        indexes = [
            models.Index(fields=['name']),
        ]

class WarehouseTransfer(models.Model):
    from_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_out')
    to_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='transfers_in')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.FloatField()
    transfer_date = models.DateTimeField(default=now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = "6.1. Warehouse Transfers"

    def __str__(self):
        return f"Transfer {self.qty} of {self.product.name} from {self.from_warehouse} to {self.to_warehouse}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.qty <= 0:
            raise ValidationError("Transfer quantity must be positive.")
        # Step 1: Fetch batches from the source warehouse using FIFO
        batches = StockBatch.get_batches_for_sale(self.product, self.qty, self.from_warehouse)
        remaining_qty_to_transfer = self.qty

        # Step 2: Process each batch for transfer
        for batch, qty_in_batch in batches:
            if remaining_qty_to_transfer <= 0:
                break
            # Reduce the quantity from the source batch
            batch.remaining_qty -= qty_in_batch
            batch.save()

            # Create or update the batch in the destination warehouse
            target_batch, created = StockBatch.objects.get_or_create(
                product=self.product,
                warehouse=self.to_warehouse,
                price=batch.price,
                purchase_item=batch.purchase_item,
                defaults={'qty': qty_in_batch, 'remaining_qty': qty_in_batch}
            )
            if not created:
                # If batch already exists in the target warehouse, increment its quantities
                target_batch.qty += qty_in_batch
                target_batch.remaining_qty += qty_in_batch
                target_batch.save()
            remaining_qty_to_transfer -= qty_in_batch
        if remaining_qty_to_transfer > 0:
            raise ValidationError(f"Not enough stock in batches for {self.product.name} in {self.from_warehouse.name}.")

        # Step 3: Update inventory (already handled by this method)
        Inventory.transfer_stock(self.product, self.from_warehouse, self.to_warehouse, self.qty)

        # Save the transfer record
        super().save(*args, **kwargs)

class MonthlyClosing(models.Model):
    month = models.DateField(default=datetime.now, unique=True)
    locked = models.BooleanField(default=False)
    previous_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.0'))  # New field

    def total_purchase_balance(self):
        total_purchases = self.purchases.aggregate(total=Sum('purchaseitem__total_amt'))['total'] or Decimal('0.0')
        total_returns = self.purchases.aggregate(total=Sum('returns__return_items__total_amt'))['total'] or Decimal('0.0')
        return total_purchases - total_returns


    def update_total_purchase_balance(self):
        """Update the total purchase balance field when a purchase is added/modified."""
        self.total_purchase_balance = self.total_purchase_balance()
        self.save(update_fields=['total_purchase_balance'])

    def total_purchase_return(self):
        return self.purchase_returns.aggregate(total=Sum('return_items__total_amt'))['total'] or Decimal('0.0')

    def total_sale_return(self):
        return self.sale_returns.aggregate(total=Sum('return_items__total_amt'))['total'] or Decimal('0.0')


    def total_sale_balance(self):
        total_sales = self.sales.aggregate(total=Sum('saleitem__total_amt') - Sum('saleitem__profit'))['total'] or Decimal('0.0')
        total_returns = self.sales.aggregate(total=Sum('returns__return_items__total_amt'))['total'] or Decimal('0.0')
        return total_sales - total_returns
    
    def update_total_sale_balance(self):
        """Update the total sale balance field when a sale is added/modified."""
        self.total_sale_balance = self.total_sale_balance()
        self.save(update_fields=['total_sale_balance'])

    def total_sale_profit(self):
        return self.sales.aggregate(
        total=Sum(F('saleitem__profit')  - F('discount_value'))
        )['total'] or Decimal('0.0')
    
    def update_total_sale_profit(self):
        """Update the total sale profit field when a sale is added/modified."""
        self.total_sale_profit = self.total_sale_profit()
        self.save(update_fields=['total_sale_profit'])

    def closing_balance(self):
        # Calculate closing balance as purchases minus sales profit
         return self.get_previous_month_closing() + self.total_purchase_balance() - self.total_sale_balance()

    def update_closing_balance(self):
        """Update the closing balance when purchase/sale is added/modified."""
        self.closing_balance = self.closing_balance()
        self.save(update_fields=['closing_balance'])

    def get_previous_month_closing(self):
        """Fetch the previous month's closing balance."""
        previous_month = (self.month.replace(day=1) - timedelta(days=1)).replace(day=1)
        previous_closing = MonthlyClosing.objects.filter(month=previous_month).first()
        return previous_closing.closing_balance() if previous_closing else Decimal('0.0')

    def net_profit_margin(self):
        """Calculate Net Profit Margin: ((Total Sale Profit - Expenses) / Total Sales) * 100"""
        total_sales = self.total_sale_balance()
        # یہاں اگر آپ کے سسٹم میں Operating Expenses ہوں تو انہیں بھی مائنس کریں
        if total_sales > 0:
            return ((self.total_sale_profit() - Decimal('0.0')) / total_sales) * 100
        return Decimal('0.0')

    def return_on_investment(self):
        """Calculate Return on Investment (ROI): Net Profit / Investment"""
        total_profit = self.total_sale_profit()
        total_investment = self.total_purchase_balance()
        if total_investment > 0:
            return (total_profit / total_investment) * 100
        return Decimal('0.0')

    

    def days_inventory_outstanding(self):
        """Calculate DIO: (Average Inventory / COGS) * 30"""
        average_inventory = Inventory.objects.aggregate(avg_stock=Sum('stock') / Inventory.objects.count())['avg_stock'] or Decimal('1.0')
        cogs = self.total_sale_balance()  # COGS = Total Sales Balance
        if cogs > 0:
            return Decimal(average_inventory) / Decimal(cogs) * 30
        return Decimal('0.0')

    

    

    def save(self, *args, **kwargs):
        """Override save to update the previous balance automatically."""
        if not self.pk:  # If creating a new record
            self.previous_balance = self.get_previous_month_closing()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.month.strftime('%B %Y')

    class Meta:
        verbose_name_plural = "9.0 Monthly Closings"
        ordering = ['-month']
        indexes = [
            models.Index(fields=['month']),
        ]
        

    def clean(self):
        """Ensure no duplicate entries for a month and validate locked status."""
        if MonthlyClosing.objects.filter(month__year=self.month.year, month__month=self.month.month).exclude(pk=self.pk).exists():
            raise ValueError(f"Monthly closing for {self.month.strftime('%B %Y')} already exists.")
        if self.locked:
            raise ValidationError(f"The month {self.month.strftime('%B %Y')} is locked and cannot be modified.")

    



                               # ( Purchase Part )
# GroupSummary Model to Summarize Balances
class GroupSummary(models.Model):
    summary_date = models.DateField(auto_now_add=True)
    total_vendor_outstanding = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_customer_outstanding = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    def calculate_totals(self):
        """Recalculate the total outstanding balances."""
        # Calculate vendor group outstanding balance
        vendor_groups = VendorGroup.objects.all()
        self.total_vendor_outstanding = sum(group.total_outstanding_balance() for group in vendor_groups)

        # Calculate customer group outstanding balance
        customer_groups = CustomerGroup.objects.all()
        self.total_customer_outstanding = sum(group.total_outstanding_balance() for group in customer_groups)

        self.save()

    class Meta:
        verbose_name_plural = "5. Group Summaries"

    def __str__(self):
        return f"Summary on {self.summary_date}"
                               
class VendorGroup(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)

    def total_outstanding_balance(self):
        return sum(vendor.outstanding_balance() for vendor in self.vendors.all())
    
    class Meta:
        verbose_name_plural = '3.1 Vendor Groups'

    def __str__(self):
        return self.name
                               
# Vendor model to store vendor details
class Vendor(models.Model):
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    group = models.ForeignKey('VendorGroup', on_delete=models.SET_NULL, null=True, blank=True, related_name='vendors')

    class Meta:
        verbose_name_plural = '3. Vendor'
        indexes = [
            models.Index(fields=['name', 'group']),
        ]

    def __str__(self):
        return self.name

    def outstanding_balance(self):
        totals = self.purchase_set.aggregate(
        total_amount=Sum('purchaseitem__total_amt'),
        total_paid=Sum('paid')
    )
        total_purchases = totals['total_amount'] or Decimal('0.0')
        total_paid = totals['total_paid'] or Decimal('0.0')
        purchase_returns = self.purchaseretrn_set.aggregate(
        total_return=Sum('return_items__total_amt')  # Use correct related_name
    )['total_return'] or Decimal('0.0')
        return total_purchases - total_paid - purchase_returns
        
# ============================================
# PURCHASE ORDER MODEL
# ============================================
class PurchaseOrder(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_no = models.CharField(max_length=20, unique=True, verbose_name="PO Number")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='purchase_orders')
    order_date = models.DateTimeField(default=now, verbose_name="Order Date")
    expected_date = models.DateField(null=True, blank=True, verbose_name="Expected Delivery Date")
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    notes = models.TextField(blank=True, null=True, verbose_name="Order Notes")
    discount_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    advance_payment = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), verbose_name="Advance Payment")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    converted_to_purchase = models.ForeignKey('Purchase', on_delete=models.SET_NULL, null=True, blank=True, related_name='converted_from_order')
    
    class Meta:
        verbose_name_plural = '4.0 Purchase Orders'
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['order_no']),
            models.Index(fields=['vendor']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"PO #{self.order_no} - {self.vendor.name}"
    
    def total_amount(self):
        return sum(item.total_amt for item in self.items.all())
    
    def total_after_discount(self):
        return self.total_amount() - self.discount_value
    
    def outstanding_advance(self):
        return self.total_after_discount() - self.advance_payment
    
    def received_qty(self, product):
        """Calculate total received qty for a product across all GRNs"""
        from django.db.models import Sum
        total = GoodsReceivedItem.objects.filter(
            grn__purchase_order=self,
            product=product
        ).aggregate(total=Sum('qty'))['total']
        return total or 0
    
    def pending_qty(self, product, order_qty):
        return order_qty - self.received_qty(product)
    
    def update_receive_status(self):
        """Auto-update status based on GRNs"""
        if self.status in ['cancelled', 'completed']:
            return
        
        items = self.items.all()
        if not items:
            return
        
        all_received = True
        any_received = False
        
        for item in items:
            received = self.received_qty(item.product)
            if received > 0:
                any_received = True
            if received < item.qty:
                all_received = False
        
        if all_received and any_received:
            self.status = 'received'
        elif any_received and not all_received:
            self.status = 'partially_received'
        
        self.save(update_fields=['status'])
    
    def save(self, *args, **kwargs):
        if not self.order_no:
            today = datetime.now().strftime('%Y%m%d')
            last_order = PurchaseOrder.objects.filter(order_no__startswith=f'PO-{today}').order_by('-order_no').first()
            if last_order:
                last_num = int(last_order.order_no.split('-')[-1])
                new_num = str(last_num + 1).zfill(4)
            else:
                new_num = '0001'
            self.order_no = f'PO-{today}-{new_num}'
        
        if not self.created_by:
            self.created_by = kwargs.pop('user', None)
        
        super().save(*args, **kwargs)


class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amt = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=Decimal('0.0'))
    
    class Meta:
        verbose_name_plural = '4.0.1 Purchase Order Items'
        unique_together = ('order', 'product')
    
    def __str__(self):
        return f"{self.qty} x {self.product.name} @ {self.price}"
    
    def save(self, *args, **kwargs):
        if self.qty <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        self.total_amt = Decimal(self.qty) * self.price
        super().save(*args, **kwargs)


# ============================================
# GOODS RECEIVED NOTE (GRN) MODEL
# ============================================
class GoodsReceivedNote(models.Model):
    GRN_REASONS = [
        ('purchase', 'Purchase Order'),
        ('direct', 'Direct Purchase'),
        ('return', 'Customer Return'),
        ('other', 'Other'),
    ]
    
    grn_no = models.CharField(max_length=20, unique=True, verbose_name="GRN Number")
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='grns', null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, verbose_name="Vendor/Supplier")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    grn_date = models.DateTimeField(default=now, verbose_name="Received Date")
    reason = models.CharField(max_length=20, choices=GRN_REASONS, default='purchase', verbose_name="Reason")
    invoice_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="Supplier Invoice No")
    vehicle_no = models.CharField(max_length=30, blank=True, null=True, verbose_name="Vehicle Number")
    driver_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Driver Name")
    notes = models.TextField(blank=True, null=True, verbose_name="Remarks")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    converted_to_purchase = models.BooleanField(default=False, verbose_name="Converted to Purchase")
    
    class Meta:
        verbose_name_plural = '4.2 Goods Received Notes'
        ordering = ['-grn_date']
        indexes = [
            models.Index(fields=['grn_no']),
            models.Index(fields=['vendor']),
            models.Index(fields=['purchase_order']),
        ]
    
    def __str__(self):
        return f"GRN #{self.grn_no} - {self.vendor.name}"
    
    def total_qty(self):
        return sum(item.qty for item in self.items.all())
    
    def total_items(self):
        return self.items.count()
    
    def save(self, *args, **kwargs):
        if not self.grn_no:
            today = datetime.now().strftime('%Y%m%d')
            last_grn = GoodsReceivedNote.objects.filter(
                grn_no__startswith=f'GRN-{today}'
            ).order_by('-grn_no').first()
            if last_grn:
                last_num = int(last_grn.grn_no.split('-')[-1])
                new_num = str(last_num + 1).zfill(4)
            else:
                new_num = '0001'
            self.grn_no = f'GRN-{today}-{new_num}'
        
        if not self.created_by:
            self.created_by = kwargs.pop('user', None)
        
        super().save(*args, **kwargs)
        
        # ✅ Update PO status after save
        if self.purchase_order and self.purchase_order.status not in ['cancelled', 'completed']:
            self.purchase_order.update_receive_status()


class GoodsReceivedItem(models.Model):
    grn = models.ForeignKey(GoodsReceivedNote, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order_qty = models.FloatField(default=0, verbose_name="Order Qty")
    qty = models.FloatField(verbose_name="Received Qty")
    pending_qty = models.FloatField(default=0, verbose_name="Pending Qty")
    unit = models.CharField(max_length=20, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amt = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=Decimal('0.0'))
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name="Remarks")
    
    class Meta:
        verbose_name_plural = '4.2.1 Goods Received Items'
    
    def __str__(self):
        return f"{self.qty}/{self.order_qty} x {self.product.name}"
    
    def save(self, *args, **kwargs):
        if not self.unit and self.product.unit:
            self.unit = self.product.unit.name
        
        self.total_amt = Decimal(self.qty) * self.price
        
        if self.order_qty > 0:
            self.pending_qty = max(0, self.order_qty - self.qty)
        
        super().save(*args, **kwargs)

class Purchase(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    bill_no = models.CharField(max_length=10, null=True, blank=True)
    waiting_for_bill = models.BooleanField(default=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    pur_date = models.DateTimeField(default=now)
    previous_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.0'), editable=False)
    paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    monthly_purchase=models.ForeignKey('MonthlyClosing', on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases', editable=False)

    class Meta:
        verbose_name_plural = '4. Purchase'
        indexes = [
            models.Index(fields=['vendor', 'pur_date']),
            models.Index(fields=['bill_no', 'warehouse']),
        ]

    def __str__(self):
        return f"Purchase Bill No. {self.bill_no} - {self.vendor.name} on {self.pur_date}"

    def total_amount(self):
        """Calculates the total amount for all items in this purchase."""
        return sum(Decimal(item.qty) * item.price for item in self.purchaseitem_set.all())

    def outstanding_balance(self):
        """Outstanding balance for this purchase."""
        return self.total_amount() - self.paid

    def outstanding_with_previous(self):
        """Outstanding balance including previous balance."""
        return self.outstanding_balance() + self.previous_balance

    def __str__(self):
        status = "Waiting for Bill" if self.waiting_for_bill else f"Bill No. {self.bill_no}"
        return f"Purchase {status} - {self.vendor.name} on {self.pur_date}"

    def bill_status(self):
        """Display status for admin."""
        return "Bill Pending" if self.waiting_for_bill else f"Bill No. {self.bill_no}"
    bill_status.short_description = 'Bill No'


    def clean(self):
        """Custom validation for conditional bill_no requirement."""
        if not self.waiting_for_bill and not self.bill_no:
            raise ValidationError({'bill_no': 'Bill number is required when the purchase is not waiting for a bill.'})
        if self.waiting_for_bill and self.bill_no:
            raise ValidationError({'bill_no': 'Bill number should not be provided if waiting for a bill.'})

    @transaction.atomic
    def save(self, *args, **kwargs):

        if not self.pk and not self.created_by:
            self.created_by = kwargs.pop('user', None)

        if not self.warehouse:
            self.warehouse = Warehouse.objects.first()

        # Check if the month is locked
        purchase_month = self.pur_date.replace(day=1)  # Get the first day of the purchase month
        

        # Get or create the MonthlyClosing instance for the purchase month
        monthly_closing, created = MonthlyClosing.objects.get_or_create(month=purchase_month)

        if monthly_closing and monthly_closing.locked:
            raise ValidationError(f"Cannot add or modify purchases for {purchase_month.strftime('%B %Y')} as the month is locked.")

        # Assign the purchase to the corresponding MonthlyClosing
        self.monthly_purchase = monthly_closing

        # Automatically set waiting_for_bill to False if a bill_no is provided
        if self.bill_no:
            self.waiting_for_bill = False

        if not self.pk:  # Calculate previous balance for new purchases only
            previous_balance = self.vendor.purchase_set.aggregate(
                outstanding=Sum('purchaseitem__total_amt') - Sum('paid')
            )['outstanding'] or Decimal('0.0')
            self.previous_balance = previous_balance
            if not self.created_by:
                self.created_by = User.objects.first()
        super().save(*args, **kwargs)

# PurchaseItem model for items in each purchase
class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    qty = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amt = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=Decimal('0.0'))

    class Meta:
        verbose_name_plural = '4.1. Purchase Items'

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.price <= 0:
            raise ValidationError("Purchase price must be greater than zero.")
        if self.qty <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        if PurchaseItem.objects.filter(purchase=self.purchase, product=self.product).exclude(pk=self.pk).exists():
            raise ValidationError(f"The product {self.product.name} is already added to this Purchase.")

        self.total_amt = Decimal(self.qty) * self.price

        warehouse = self.purchase.warehouse
        if self.pk:  # Update existing item
            existing_item = PurchaseItem.objects.get(pk=self.pk)
            qty_diff = self.qty - existing_item.qty
            batch = StockBatch.objects.filter(purchase_item=self).first()
            if batch:
                batch.remaining_qty += qty_diff
                batch.qty += qty_diff
                batch.price = self.price
                batch.save()
            Inventory.update_stock(self.product, qty_diff, warehouse)
        else:  # New item
            super().save(*args, **kwargs)  # Save first to get PK
            StockBatch.add_batch(self.product, self.qty, self.price, purchase_item=self, warehouse=warehouse)
            Inventory.update_stock(self.product, self.qty, warehouse)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.qty} x {self.product.name}"

                               # ( Sale Part )
# CustomerGroup model to group customers together
class CustomerGroup(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)

    def total_outstanding_balance(self):
        return sum(customer.adjusted_outstanding_balance() for customer in self.customers.all())

    class Meta:
        verbose_name_plural = '2.1 Customer Groups'

    def __str__(self):
        return self.name

# Customer model to store customer details
class Customer(models.Model):
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15, null=True, blank=True)  # New field
    ref_name_1=models.CharField(max_length=100, null=True, blank=True)
    ref_contact_number_1=models.CharField(max_length=15, null=True, blank=True)
    ref_name_2=models.CharField(max_length=100, null=True, blank=True)
    ref_contact_number_2=models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)  # New field
    profit_margin = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('0.00'), 
        help_text="Set profit margin percentage (e.g., 20.00 for 20%)"
    )  # New field for profit margin
    group = models.ForeignKey('CustomerGroup', on_delete=models.SET_NULL, null=True, blank=True, related_name='customers')

    class Meta:
        verbose_name_plural = '2. Customers'
        indexes = [
            models.Index(fields=['name', 'group']),  # Composite index
        ]

    def __str__(self):
        return self.name

    def adjusted_outstanding_balance(self):
        # Calculate the total outstanding balance from sales
        total_outstanding = self.sale_set.aggregate(
            total=(Sum('saleitem__total_amt') - Sum('discount_value')) - Sum('paid')
        )['total'] or Decimal('0.0')

        # Calculate the total amount returned in sale returns
        total_returned = SaleRetrn.objects.filter(sale__customer=self).aggregate(
            total_returned=Sum('return_items__total_amt')
        )['total_returned'] or Decimal('0.0')

        # Subtract the returned amount from the outstanding balance
        adjusted_balance = total_outstanding - total_returned

        return adjusted_balance

# Sale model for sales transactions
class Sale(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=False, blank=False, related_name='sales')
    bill_no = models.CharField(max_length=10) 
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    sale_date = models.DateTimeField(default=now)
    paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    previous_balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.0'), editable=False)
    discount_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, editable=False)
    monthly_sale=models.ForeignKey('MonthlyClosing', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales', editable=False)

    class Meta:
        verbose_name_plural = '5. Sales'

    def total_amount_without_profit(self):
        total_cost = Decimal('0.0')
        for item in self.saleitem_set.all():
            batches = StockBatch.get_batches_for_sale(item.product, item.qty)
            item_cost = sum(Decimal(qty_in_batch) * batch.price for batch, qty_in_batch in batches)
            total_cost += item_cost
        return total_cost

    def __str__(self):
        return f"Sale Bill No. {self.bill_no} - {self.customer.name} on {self.sale_date}"

    def total_without_discount(self):
        """Calculates the total amount for all items in this sale without discount."""
        return sum(item.total_amt for item in self.saleitem_set.all())

    def total_amount(self):
        """Calculates the total amount for all items in this sale, considering only a fixed discount."""
        total = self.total_without_discount()
        discount = self.discount_value  # Always treat discount as a fixed amount
        return total - discount

    def total_profit(self):
        total_profit = self.saleitem_set.aggregate(total=Sum('profit'))['total']
        total_profit = total_profit if total_profit is not None else Decimal('0.0')
        return total_profit - self.discount_value
    
    def outstanding_balance(self):
        """Calculates the outstanding balance for the sale, considering the discount."""
        return self.total_amount() - self.paid

    @property
    def total_outstanding_with_previous(self):
        """Calculates the total outstanding balance including the previous balance."""
        return self.previous_balance + self.outstanding_balance()

    @transaction.atomic
    def save(self, *args, **kwargs):

        if not self.pk and not self.created_by:
            self.created_by = kwargs.pop('user', None)

        if not self.warehouse_id:  # اگر ویئرہاؤس سیٹ نہیں ہے
            default_warehouse = Warehouse.objects.first()
            if not default_warehouse:
                raise ValidationError("کوئی ویئرہاؤس موجود نہیں ہے۔ براہ کرم پہلے ایک ویئرہاؤس بنائیں۔")
            self.warehouse = default_warehouse

       

        # Check if the month is locked
        sale_month = self.sale_date.replace(day=1)  # Get the first day of the sale month
        # Get or create the MonthlyClosing instance for the purchase month
        monthly_closing, created = MonthlyClosing.objects.get_or_create(month=sale_month)

        if monthly_closing and monthly_closing.locked:
            raise ValidationError(f"Cannot add or modify sales for {sale_month.strftime('%B %Y')} as the month is locked.")

        # Assign the purchase to the corresponding MonthlyClosing
        self.monthly_sale = monthly_closing
        
        if not self.pk:  # Only calculate for new entries
            previous_sales_balance = self.customer.sale_set.annotate(
                total_amount=Sum('saleitem__total_amt')
            ).aggregate(
                total_balance=Sum(F('saleitem__total_amt')) - Sum(F('discount_value')) - Sum(F('paid'))
            )['total_balance']

            self.previous_balance = previous_sales_balance if previous_sales_balance else Decimal('0.0')
            # Set the created_by field if not set
            if self.created_by is None:
                self.created_by = kwargs.get('user')

        super().save(*args, **kwargs)


class SaleItem(models.Model):
    sale = models.ForeignKey('Sale', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    qty = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Optional")
    total_amt = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=Decimal('0.0'))
    profit = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=Decimal('0.0'))
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.0'), editable=False)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    batches_used = models.ManyToManyField('StockBatch', blank=True, related_name='sale_items')  # New field

    class Meta:
        verbose_name_plural = '5.1. Sale Items'

    def get_fifo_price(self):
        """Fetch FIFO price from stock batches using the sale's warehouse."""
        warehouse = self.sale.warehouse
        if not warehouse:
            raise ValidationError(f"Warehouse must be specified for sale {self.sale.bill_no} to calculate FIFO price.")
        batches = StockBatch.get_batches_for_sale(self.product, self.qty, warehouse)
        total_cost = sum(Decimal(qty_in_batch) * batch.price for batch, qty_in_batch in batches)
        total_qty = sum(qty_in_batch for _, qty_in_batch in batches)
        if total_qty < self.qty:
            raise ValidationError(f"Insufficient stock batches for {self.product.name} in {warehouse.name}.")
        return total_cost / Decimal(total_qty) if total_qty > 0 else Decimal('0.0')

    def calculate_sale_price(self, fifo_price):
        """Calculate sale price using FIFO price + profit margin."""
        customer_profit_margin = self.sale.customer.profit_margin or Decimal('0.0')
        return fifo_price * (1 + customer_profit_margin / 100)

    def validate_and_update_stock(self):
        """Validate stock and update inventory for a specific warehouse."""
        warehouse = self.sale.warehouse
        if not warehouse:
            raise ValidationError(f"Warehouse must be specified for sale {self.sale.bill_no}.")
        batches = StockBatch.get_batches_for_sale(self.product, self.qty, warehouse)
        remaining_qty = self.qty
        total_cost = Decimal('0.0')
        used_batches = []

        for batch, qty_in_batch in batches:
            if remaining_qty <= 0:
                break
            batch.remaining_qty -= qty_in_batch
            batch.save()
            total_cost += Decimal(qty_in_batch) * batch.price
            remaining_qty -= qty_in_batch
            used_batches.append(batch)

        Inventory.update_stock(self.product, -self.qty, warehouse)
        return total_cost, used_batches

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.qty <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        
        # Ensure Sale is saved first
        if not self.sale.pk:
            self.sale.save()

        warehouse = self.sale.warehouse
        if not warehouse:
            raise ValidationError(f"Warehouse is not set for sale {self.sale.bill_no}.")

        current_stock = Inventory.get_stock(self.product, warehouse)
        if self.qty > current_stock:
            raise ValidationError(f"Insufficient stock for {self.product.name} in {warehouse.name}. Available: {current_stock}, Requested: {self.qty}")

        fifo_price = self.get_fifo_price()
        recommended_price = self.calculate_sale_price(fifo_price)
        self.price = Decimal(self.price) if self.price else recommended_price

        if self.price < recommended_price:
            raise ValidationError(f"Sale price for {self.product.name} must be at least {recommended_price:.2f}")

        total_cost, used_batches = self.validate_and_update_stock()
        self.total_amt = Decimal(self.qty) * self.price
        total_sale_amount = self.sale.total_without_discount()
        discount_ratio = self.total_amt / total_sale_amount if total_sale_amount > 0 else Decimal('0.0')
        self.discount = discount_ratio * self.sale.discount_value
        self.profit = self.total_amt - total_cost

        super().save(*args, **kwargs)
        if used_batches:
            self.batches_used.set(used_batches)

    def __str__(self):
        return f"{self.qty} x {self.product.name} at {self.price:.2f}"
        
# 
class SaleOrder(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('ready', 'Ready to Ship'),
        ('partially_delivered', 'Partially Delivered'),  # ✅ New
        ('delivered', 'Delivered'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled'),
    ]
    
    order_no = models.CharField(max_length=20, unique=True, verbose_name="Order Number")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(default=now, verbose_name="Order Date")
    delivery_date = models.DateField(null=True, blank=True, verbose_name="Expected Delivery Date")
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    notes = models.TextField(blank=True, null=True, verbose_name="Order Notes")
    discount_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    advance_payment = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), verbose_name="Advance Payment")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    converted_to_sale = models.ForeignKey('Sale', on_delete=models.SET_NULL, null=True, blank=True, related_name='converted_from_order')
    
    class Meta:
        verbose_name_plural = '5.0 Sale Orders'
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['order_no']),
            models.Index(fields=['customer']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Order #{self.order_no} - {self.customer.name}"
    
    def total_amount(self):
        return sum(item.total_amt for item in self.items.all())
    
    def total_after_discount(self):
        return self.total_amount() - self.discount_value
    
    def outstanding_advance(self):
        return self.total_after_discount() - self.advance_payment
    
    def delivered_qty(self, product):
        """Calculate total delivered qty for a product across all challans"""
        from django.db.models import Sum
        total = DeliveryChallanItem.objects.filter(
            challan__order=self,
            product=product
        ).aggregate(total=Sum('qty'))['total']
        return total or 0
    
    def pending_qty(self, product, order_qty):
        """Calculate pending qty"""
        return order_qty - self.delivered_qty(product)
    
    def update_delivery_status(self):
        """Auto-update status based on deliveries"""
        if self.status in ['cancelled', 'invoiced']:
            return
        
        items = self.items.all()
        if not items:
            return
        
        all_delivered = True
        any_delivered = False
        
        for item in items:
            delivered = self.delivered_qty(item.product)
            if delivered > 0:
                any_delivered = True
            if delivered < item.qty:
                all_delivered = False
        
        if all_delivered and any_delivered:
            self.status = 'delivered'
        elif any_delivered and not all_delivered:
            self.status = 'partially_delivered'
        
        self.save(update_fields=['status'])
    
    def save(self, *args, **kwargs):
        if not self.order_no:
            today = datetime.now().strftime('%Y%m%d')
            last_order = SaleOrder.objects.filter(order_no__startswith=f'ORD-{today}').order_by('-order_no').first()
            if last_order:
                last_num = int(last_order.order_no.split('-')[-1])
                new_num = str(last_num + 1).zfill(4)
            else:
                new_num = '0001'
            self.order_no = f'ORD-{today}-{new_num}'
        
        if not self.created_by:
            self.created_by = kwargs.pop('user', None)
        
        super().save(*args, **kwargs)
        
class SaleOrderItem(models.Model):
    order = models.ForeignKey(SaleOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    qty = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amt = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=Decimal('0.0'))
    reserved = models.BooleanField(default=False, help_text="Reserve this stock for the order")
    
    class Meta:
        verbose_name_plural = '5.0.1 Sale Order Items'
        unique_together = ('order', 'product')
    
    def __str__(self):
        return f"{self.qty} x {self.product.name} @ {self.price}"
    
    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.qty <= 0:
            raise ValidationError("Quantity must be greater than zero.")
        
        self.total_amt = Decimal(self.qty) * self.price
        
        is_new = self.pk is None
        old_reserved = False
        old_qty = 0
        
        if not is_new:
            old_item = SaleOrderItem.objects.get(pk=self.pk)
            old_reserved = old_item.reserved
            old_qty = old_item.qty
        
        super().save(*args, **kwargs)
        
        if self.reserved and self.order.status not in ['cancelled', 'invoiced']:
            try:
                inventory = Inventory.objects.get(
                    product=self.product, 
                    warehouse=self.order.warehouse
                )
                
                if is_new:
                    qty_to_reserve = self.qty
                else:
                    if old_reserved:
                        qty_to_reserve = self.qty - old_qty
                    else:
                        qty_to_reserve = self.qty
                
                if qty_to_reserve > 0:
                    if inventory.available_stock < qty_to_reserve:
                        raise ValidationError(
                            f"Insufficient stock to reserve. Available: {inventory.available_stock}, Required: {qty_to_reserve}"
                        )
                    inventory.reserved_stock += qty_to_reserve
                    inventory.save()
                    
            except Inventory.DoesNotExist:
                raise ValidationError(f"No inventory for {self.product.name} in {self.order.warehouse.name}")
        
        elif not self.reserved and not is_new and old_reserved:
            try:
                inventory = Inventory.objects.get(
                    product=self.product, 
                    warehouse=self.order.warehouse
                )
                inventory.reserved_stock = max(0, inventory.reserved_stock - old_qty)
                inventory.save()
            except Inventory.DoesNotExist:
                pass

# ============================================
# DELIVERY CHALLAN MODEL
# ============================================
class DeliveryChallan(models.Model):
    CHALLAN_REASONS = [
        ('sale', 'Sale'),
        ('transfer', 'Stock Transfer'),
        ('job_work', 'Job Work'),
        ('approval', 'On Approval'),
        ('return', 'Return to Vendor'),
        ('other', 'Other'),
    ]
    
    challan_no = models.CharField(max_length=20, unique=True, verbose_name="Challan Number")
    order = models.ForeignKey(SaleOrder, on_delete=models.CASCADE, related_name='challans', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name="Customer/Receiver")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    challan_date = models.DateTimeField(default=now, verbose_name="Challan Date")
    reason = models.CharField(max_length=20, choices=CHALLAN_REASONS, default='sale', verbose_name="Reason for Dispatch")
    vehicle_no = models.CharField(max_length=30, blank=True, null=True, verbose_name="Vehicle Number")
    transport_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Transport Company")
    driver_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Driver Name")
    driver_contact = models.CharField(max_length=15, blank=True, null=True, verbose_name="Driver Contact")
    notes = models.TextField(blank=True, null=True, verbose_name="Remarks")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    converted_to_sale = models.BooleanField(default=False, verbose_name="Converted to Invoice")
    
    class Meta:
        verbose_name_plural = '5.2 Delivery Challans'
        ordering = ['-challan_date']
        indexes = [
            models.Index(fields=['challan_no']),
            models.Index(fields=['customer']),
            models.Index(fields=['order']),
        ]
    
    def __str__(self):
        return f"Challan #{self.challan_no} - {self.customer.name}"
    
    def total_qty(self):
        return sum(item.qty for item in self.items.all())
    
    def total_items(self):
        return self.items.count()
    
    def save(self, *args, **kwargs):
        if not self.challan_no:
            today = datetime.now().strftime('%Y%m%d')
            last_challan = DeliveryChallan.objects.filter(
                challan_no__startswith=f'DC-{today}'
            ).order_by('-challan_no').first()
            if last_challan:
                last_num = int(last_challan.challan_no.split('-')[-1])
                new_num = str(last_num + 1).zfill(4)
            else:
                new_num = '0001'
            self.challan_no = f'DC-{today}-{new_num}'
        
        if not self.created_by:
            self.created_by = kwargs.pop('user', None)
        
        super().save(*args, **kwargs)
        
        # ✅ Order status update after save
        if self.order and self.order.status not in ['cancelled', 'invoiced']:
            self.order.update_delivery_status()


class DeliveryChallanItem(models.Model):
    challan = models.ForeignKey(DeliveryChallan, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order_qty = models.FloatField(default=0, verbose_name="Order Qty")
    qty = models.FloatField(verbose_name="Delivery Qty")
    pending_qty = models.FloatField(default=0, verbose_name="Pending Qty")
    unit = models.CharField(max_length=20, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Price (Optional)")
    total_amt = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=Decimal('0.0'))
    sale_item = models.ForeignKey(SaleItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='challan_items')
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name="Item Remarks")
    
    class Meta:
        verbose_name_plural = '5.2.1 Delivery Challan Items'
    
    def __str__(self):
        return f"{self.qty}/{self.order_qty} x {self.product.name}"
    
    def save(self, *args, **kwargs):
        if not self.unit and self.product.unit:
            self.unit = self.product.unit.name
        
        self.total_amt = Decimal(self.qty) * self.price
        
        # ✅ Pending qty auto-calculate
        if self.order_qty > 0:
            self.pending_qty = max(0, self.order_qty - self.qty)
        
        super().save(*args, **kwargs)

# StockBatch model for managing FIFO stock batches
class StockBatch(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_index=True)
    qty = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    remaining_qty = models.FloatField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    purchase_item = models.ForeignKey(
        'PurchaseItem', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='stock_batches'  # For reverse relation
    )

    class Meta:
        ordering = ['-id']  # FIFO ordering
        verbose_name_plural = '7.1 Batches'
        unique_together = ('product', 'warehouse', 'purchase_item')

    @classmethod
    def add_batch(cls, product, qty, price, purchase_item=None, warehouse=None):
        """Add a new batch to a specific warehouse."""
        if not warehouse:
            raise ValidationError("Warehouse must be specified for adding a batch.")
        batch = cls.objects.create(
            product=product, qty=qty, price=price, remaining_qty=qty,
            purchase_item=purchase_item, warehouse=warehouse
        )
        return batch

    @classmethod
    def get_batches_for_sale(cls, product, qty, warehouse=None):
        """Retrieve batches for sale from a specific warehouse."""
        if not warehouse:
            raise ValidationError("Warehouse must be specified for batch retrieval.")
        batches = []
        remaining_qty = qty
        for batch in cls.objects.filter(product=product, warehouse=warehouse, remaining_qty__gt=0).order_by('id'):
            if remaining_qty <= 0:
                break
            qty_in_batch = min(remaining_qty, batch.remaining_qty)
            batches.append((batch, qty_in_batch))
            remaining_qty -= qty_in_batch
        if remaining_qty > 0:
            raise ValidationError(f"Not enough stock for {product.name} in {warehouse.name}. Required: {qty}, Available: {qty - remaining_qty}")
        return batches

    def __str__(self):
        return f"Batch of {self.product.name} - {self.qty} units at {self.price} in {self.warehouse.name}"

# Inventory model to track stock levels for each product
class Inventory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    stock = models.FloatField(default=0, editable=False)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    reserved_stock = models.FloatField(default=0, editable=False)  # New field for reserved stock

    class Meta:
        verbose_name_plural = '7. Inventory'
        unique_together = ('product', 'warehouse')
        indexes = [
            models.Index(fields=['product', 'warehouse']),  # Composite index
        ]

    @classmethod
    def send_bulk_low_stock_alert(cls):
        """Send a single email with all low-stock products"""
        low_stock_items = cls.objects.filter(stock__lt=F('product__low_stock_threshold'))
        
        if low_stock_items.exists():
            subject = "Low Stock Alert for Multiple Products"
            message = "The following products are running low on stock:\n\n"

            for item in low_stock_items:
                message += f"- {item.product.name}: {item.stock} left (Minimum Qty: {item.product.low_stock_threshold})\n"

            message += "\nPlease take necessary action to restock these items."
            
            send_mail(
                subject, 
                message, 
                'umershahzadbh1@gmail.com', 
                ['umershahzadbh1@gmail.com']
            )

    @classmethod
    def check_low_stock(cls):
        """Fetch all products that are low in stock"""
        return cls.objects.filter(stock__lt=F('product__low_stock_threshold'))

    def is_low_stock(self):
        """Check if stock is below the low stock threshold"""
        return self.stock < self.product.low_stock_threshold

    @classmethod
    def get_stock(cls, product, warehouse=None):
        """Returns the current stock level for a product in a specific warehouse."""
        if warehouse:
            inventory = cls.objects.filter(product=product, warehouse=warehouse).first()
        else:
            inventory = cls.objects.filter(product=product).first()  # Fallback to any warehouse
        return inventory.stock if inventory else 0.0

    @property
    def available_stock(self):
        """Calculates stock available for new sales."""
        return self.stock - self.reserved_stock

    @classmethod
    def update_reserved_stock(cls, product, qty_delta):
        """Updates reserved stock for a product."""
        inventory, _ = cls.objects.get_or_create(product=product)
        inventory.reserved_stock += qty_delta
        if inventory.reserved_stock < 0:
            raise ValidationError(f"Reserved stock cannot be negative for {product.name}.")
        inventory.save()

    @classmethod
    def update_stock(cls, product, qty_delta, warehouse=None):
        """Updates stock for a product in a specific warehouse."""
        if not warehouse:
            raise ValidationError("Warehouse must be specified for stock updates.")
        inventory, _ = cls.objects.get_or_create(product=product, warehouse=warehouse)
        inventory.stock += qty_delta
        if inventory.stock < 0:
            raise ValidationError(f"Stock cannot be negative for {product.name} in {warehouse.name}.")
        inventory.save()

    @classmethod
    def transfer_stock(cls, product, from_warehouse, to_warehouse, qty):
        """Transfer stock between warehouses."""
        if qty <= 0:
            raise ValidationError("Transfer quantity must be positive.")
        from_inventory = cls.objects.get(product=product, warehouse=from_warehouse)
        if from_inventory.stock < qty:
            raise ValidationError(f"Insufficient stock in {from_warehouse.name} for transfer.")
        
        cls.update_stock(product, -qty, from_warehouse)
        cls.update_stock(product, qty, to_warehouse)
        logger.info(f"Transferred {qty} units of {product.name} from {from_warehouse.name} to {to_warehouse.name}")

    @classmethod
    def check_stock_availability(cls, product, required_qty):
        """Checks if sufficient stock is available."""
        inventory = cls.objects.get(product=product)
        if inventory.stock < required_qty:
            raise ValidationError(f"Insufficient stock for {product.name}. Available: {inventory.stock}, Required: {required_qty}")

    def stock_value(self):
        """Calculates the total stock value based on remaining batch quantities."""
        return sum(Decimal(batch.remaining_qty) * batch.price for batch in StockBatch.objects.filter(product=self.product,warehouse=self.warehouse))

    def check_low_stock(self):
        """Checks if stock is below the threshold."""
        if self.stock < self.product.low_stock_threshold:
            return True
        return False

    def __str__(self):
        return f"{self.product.name} - {self.stock} units in {self.warehouse.name}"

class PurchaseRetrn(models.Model):
    bill_no = models.CharField(max_length=10)
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="returns", null=True,blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    purchase_return_date = models.DateTimeField(default=now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    return_reason = models.CharField(
    max_length=255,choices=[
        ('damaged', 'Damaged Goods'),
        ('incorrect', 'Incorrect Shipment'),
        ('expired', 'Expired Stock'),
        ('other', 'Other'),],default='other',)
    monthly_purchase = models.ForeignKey(
        MonthlyClosing, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_returns', editable=False
    )


    @transaction.atomic
    def save(self, *args, **kwargs):

        if not self.pk and not self.created_by:
            self.created_by = kwargs.pop('user', None)
        
        purchase_month = self.purchase_return_date.replace(day=1)
        monthly_closing, _ = MonthlyClosing.objects.get_or_create(month=purchase_month)
        self.monthly_purchase = monthly_closing

        if monthly_closing.locked:
            raise ValidationError(f"Cannot process purchase return for {purchase_month.strftime('%B %Y')}, as the month is locked.")
        self.monthly_purchase = monthly_closing

        if not self.created_by:
            self.created_by = User.objects.first()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name_plural = '4.3. Purchase Retrn'

    def __str__(self):
        return f"Return for  {self.vendor.name} on {self.purchase_return_date}"


class PurchaseRetrnItem(models.Model):
    purchase_return = models.ForeignKey(
        'PurchaseRetrn',
        on_delete=models.CASCADE,
        related_name="return_items",
        null=True,
        blank=True
    )
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    qty = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amt = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=Decimal('0.0'))

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Ensure quantity is positive
        if self.qty <= 0:
            raise ValidationError("Quantity must be positive.")

        # Calculate the total amount
        self.total_amt = Decimal(self.qty) * self.price

        if self.pk:
            # If this is an update to an existing return item
            existing_purchase_return_item = PurchaseRetrnItem.objects.get(pk=self.pk)
            qty_diff = self.qty - existing_purchase_return_item.qty  # Quantity difference

            # Adjust the stock batches for the product and price
            self.adjust_batches(-qty_diff)

            # Update stock levels
            Inventory.update_stock(self.product, -qty_diff)
        else:
            # For new return items, adjust the stock batches without creating new ones
            self.adjust_batches(-self.qty)

            # Update stock levels
            Inventory.update_stock(self.product, -self.qty)

        # Validate the return item against the original purchase
        self.validate_purchase_item()

        # Save the item
        super().save(*args, **kwargs)

    def adjust_batches(self, qty_diff):
        """
        Adjusts stock batches for the given quantity difference.
        """
        remaining_qty_to_adjust = abs(qty_diff)
        batches = StockBatch.objects.filter(product=self.product, price=self.price).order_by('id')

        for batch in batches:
            if qty_diff < 0:  # Returning stock, decrease batch quantities
                decrement = min(batch.remaining_qty, remaining_qty_to_adjust)
                batch.remaining_qty -= decrement
                batch.qty -= decrement
                batch.save()
                remaining_qty_to_adjust -= decrement

                if remaining_qty_to_adjust <= 0:
                    break
            else:  # Removing return, increase batch quantities
                increment = min(batch.qty - batch.remaining_qty, remaining_qty_to_adjust)
                batch.remaining_qty += increment
                batch.qty += increment
                batch.save()
                remaining_qty_to_adjust -= increment

                if remaining_qty_to_adjust <= 0:
                    break

        if remaining_qty_to_adjust > 0:
            if qty_diff < 0:
                raise ValidationError(
                    f"Cannot return {abs(qty_diff)} units. Not enough stock in batches for product {self.product.name}."
                )
            else:
                raise ValidationError(
                    f"Cannot undo return of {abs(qty_diff)} units. No additional stock available for product {self.product.name}."
                )

    def validate_purchase_item(self):
        """
        Validate the product, quantity, and price against the selected purchase.
        """
        purchase = self.purchase_return.purchase  # Selected purchase from return
        purchase_item = purchase.purchaseitem_set.filter(product=self.product).first()

        if not purchase_item:
            raise ValidationError(f"The product '{self.product}' does not exist in the selected purchase.")

        if self.price != purchase_item.price:
            raise ValidationError(
                f"Price mismatch: Purchase price is {purchase_item.price}, but return price is {self.price}."
            )

        if self.qty > purchase_item.qty:
            raise ValidationError(
                f"Quantity exceeds purchase limit: Purchased quantity is {purchase_item.qty}, but return quantity is {self.qty}."
            )

    def __str__(self):
        return f"{self.qty} x {self.product.name}"

    class Meta:
        verbose_name_plural = '4.4. Purchase Return Items'



class SaleRetrn(models.Model):
    bill_no = models.CharField(max_length=10)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="returns", null=True,blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    sale_return_date = models.DateTimeField(default=now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    return_reason = models.CharField(
    max_length=255,choices=[
        ('damaged', 'Damaged Goods'),
        ('incorrect', 'Incorrect Shipment'),
        ('expired', 'Expired Stock'),
        ('other', 'Other'),],default='other',)
    monthly_sale = models.ForeignKey(MonthlyClosing, on_delete=models.SET_NULL, null=True, blank=True, related_name='sale_returns', editable=False)


    @transaction.atomic
    def save(self, *args, **kwargs):

        if not self.pk and not self.created_by:
            self.created_by = kwargs.pop('user', None)
        
        sale_month = self.sale_return_date.replace(day=1)
        monthly_closing, _ = MonthlyClosing.objects.get_or_create(month=sale_month)
        self.monthly_sale = monthly_closing

        if monthly_closing.locked:
            raise ValidationError(f"Cannot process sale return for {sale_month.strftime('%B %Y')}, as the month is locked.")
        self.monthly_sale = monthly_closing
        
        if not self.created_by:
            self.created_by = User.objects.first()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name_plural = '5.3. Sale Retrn'

    def __str__(self):
        return f"Return for  {self.customer.name} on {self.sale_return_date}"


class SaleRetrnItem(models.Model):
    sale_return = models.ForeignKey(
        'SaleRetrn',
        on_delete=models.CASCADE,
        related_name="return_items",
        null=True,
        blank=True
    )
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    qty = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amt = models.DecimalField(max_digits=15, decimal_places=2, editable=False, default=Decimal('0.0'))

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Ensure quantity is positive
        if self.qty <= 0:
            raise ValidationError("Quantity must be positive.")

        # Calculate the total amount
        self.total_amt = Decimal(self.qty) * self.price

        if self.pk:
            # If this is an update to an existing return item
            existing_sale_return_item = SaleRetrnItem.objects.get(pk=self.pk)
            qty_diff = self.qty - existing_sale_return_item.qty  # Quantity difference

            # Adjust the stock batches for the product and price
            self.adjust_batches(qty_diff)

            # Update stock levels
            Inventory.update_stock(self.product, qty_diff)
        else:
            # For new return items, adjust the stock batches
            self.adjust_batches(self.qty)

            # Update stock levels
            Inventory.update_stock(self.product, self.qty)

        # Validate the return item against the original purchase
        self.validate_sale_item()

        # Save the item
        super().save(*args, **kwargs)

    def adjust_batches(self, qty_diff):
        """
        Adjusts stock batches for the given quantity difference without modifying batch 'qty'.
        """
        remaining_qty_to_adjust = abs(qty_diff)
        batches = StockBatch.objects.filter(product=self.product, price=self.price).order_by('id')

        for batch in batches:
            if qty_diff < 0:  # Returning stock, decrease remaining batch quantities
                decrement = min(batch.remaining_qty, remaining_qty_to_adjust)
                batch.remaining_qty -= decrement
                batch.save()
                remaining_qty_to_adjust -= decrement

                if remaining_qty_to_adjust <= 0:
                    break
            else:  # Removing return, increase remaining batch quantities
                increment = min(batch.qty - batch.remaining_qty, remaining_qty_to_adjust)
                batch.remaining_qty += increment
                batch.save()
                remaining_qty_to_adjust -= increment

                if remaining_qty_to_adjust <= 0:
                    break

        if remaining_qty_to_adjust > 0:
            if qty_diff < 0:
                raise ValidationError(
                    f"Cannot return {abs(qty_diff)} units. Not enough stock in batches for product {self.product.name}."
                )
            else:
                raise ValidationError(
                    f"Cannot undo return of {abs(qty_diff)} units. No additional stock available for product {self.product.name}."
                )

    def validate_sale_item(self):
        """
        Validate the product, quantity, and price against the selected purchase.
        """
        sale = self.sale_return.sale  # Selected sale from return
        sale_item = sale.saleitem_set.filter(product=self.product).first()

        if not sale_item:
            raise ValidationError(f"The product '{self.product}' does not exist in the selected sale.")

        if self.price != sale_item.price:
            raise ValidationError(
                f"Price mismatch: Sale price is {sale_item.price}, but return price is {self.price}."
            )

        if self.qty > sale_item.qty:
            raise ValidationError(
                f"Quantity exceeds sale limit: Sale quantity is {sale_item.qty}, but return quantity is {self.qty}."
            )

    def __str__(self):
        return f"{self.qty} x {self.product.name}"

    class Meta:
        verbose_name_plural = '5.4. Sale Return Items'


class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
    ]

    adjustment_type = models.CharField(max_length=10, choices=ADJUSTMENT_TYPES)
    reason = models.CharField(max_length=255)
    adjustment_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name_plural = "8.0 Stock Adjustments"

    def __str__(self):
        return f"{self.get_adjustment_type_display()} - {self.reason} on {self.adjustment_date}"


class StockAdjustmentItem(models.Model):
    adjustment = models.ForeignKey('StockAdjustment', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    qty = models.FloatField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), editable=False)

    class Meta:
        verbose_name_plural = "8.1. Stock Adjustment Items"

    @transaction.atomic
    def save(self, *args, **kwargs):
        # Validate quantity
        if self.qty <= 0:
            raise ValidationError("Adjustment quantity must be positive.")

        # Fetch inventory for the product
        inventory, _ = Inventory.objects.get_or_create(product=self.product)
        
        # ✅ Warehouse determine karo
        warehouse = inventory.warehouse if inventory.warehouse else Warehouse.objects.first()

        if self.adjustment.adjustment_type == 'decrease':
            # Validate stock availability
            if inventory.available_stock < self.qty:
                raise ValidationError(
                    f"Insufficient stock for {self.product.name}. Available: {inventory.available_stock}, Required: {self.qty}."
                )
            
            # FIFO Logic for price and stock adjustment
            remaining_qty = self.qty
            total_price = Decimal('0.00')
            batches = StockBatch.objects.filter(product=self.product, remaining_qty__gt=0).order_by('id')
            for batch in batches:
                if remaining_qty <= 0:
                    break
                deduct_qty = min(batch.remaining_qty, remaining_qty)
                total_price += Decimal(deduct_qty) * batch.price
                batch.remaining_qty -= deduct_qty
                batch.save()
                remaining_qty -= deduct_qty

            self.price = total_price / Decimal(self.qty)  # Average price from batches
            Inventory.update_stock(self.product, -self.qty, warehouse=warehouse)

        else:  # Adjustment type: increase
            if self.price <= 0:
                raise ValidationError("Price must be greater than zero for stock increases.")
            Inventory.update_stock(self.product, self.qty, warehouse=warehouse)
            StockBatch.add_batch(self.product, self.qty, self.price, warehouse=warehouse)

        # Calculate total value
        self.total_value = Decimal(self.qty) * self.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Adjustment for {self.product.name} - {self.qty} units at {self.price} each"

class License(models.Model):
    key = models.CharField(max_length=255, unique=True)  # License Key
    expiry_date = models.DateField()  # Expiration Date
    created_at = models.DateTimeField(auto_now_add=True)  # When the key was created
    is_active = models.BooleanField(default=True)

    def is_valid(self):
        """Check if the license is still valid."""
        return self.expiry_date >= now().date()

    @staticmethod
    def generate_license_key(secret):
        """Generate a hash-based license key using a secret string."""
        return hashlib.sha256(secret.encode()).hexdigest()

    def save(self, *args, **kwargs):
        """Ensure only programmers can set the license key."""
        if not self.key:
            raise ValidationError("License key cannot be empty.")
        if not self.expiry_date:
            raise ValidationError("Expiry date must be set.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"License (Valid till {self.expiry_date})"
        
        
# ============================================
# STOCK AUDIT MODEL
# ============================================
class StockAudit(models.Model):
    AUDIT_STATUS = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    audit_no = models.CharField(max_length=20, unique=True, verbose_name="Audit Number")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    audit_date = models.DateTimeField(default=now, verbose_name="Audit Date")
    status = models.CharField(max_length=20, choices=AUDIT_STATUS, default='draft')
    notes = models.TextField(blank=True, null=True, verbose_name="Audit Notes")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_variance_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.0'))
    
    class Meta:
        verbose_name_plural = '7.2 Stock Audits'
        ordering = ['-audit_date']
        indexes = [
            models.Index(fields=['audit_no']),
            models.Index(fields=['warehouse']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Audit #{self.audit_no} - {self.warehouse.name}"
    
    def total_items(self):
        return self.items.count()
    
    def items_with_variance(self):
        return self.items.filter(system_qty__gt=0, physical_qty__isnull=False)
    
    def save(self, *args, **kwargs):
        if not self.audit_no:
            today = datetime.now().strftime('%Y%m%d')
            last_audit = StockAudit.objects.filter(
                audit_no__startswith=f'AUD-{today}'
            ).order_by('-audit_no').first()
            if last_audit:
                last_num = int(last_audit.audit_no.split('-')[-1])
                new_num = str(last_num + 1).zfill(4)
            else:
                new_num = '0001'
            self.audit_no = f'AUD-{today}-{new_num}'
        
        if not self.created_by:
            self.created_by = kwargs.pop('user', None)
        
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = now()
        
        super().save(*args, **kwargs)


class StockAuditItem(models.Model):
    audit = models.ForeignKey(StockAudit, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    system_qty = models.FloatField(default=0, verbose_name="System Stock")
    physical_qty = models.FloatField(null=True, blank=True, verbose_name="Physical Count")
    variance = models.FloatField(default=0, verbose_name="Variance (+/-)")
    unit = models.CharField(max_length=20, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.0'))
    variance_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.0'))
    notes = models.CharField(max_length=255, blank=True, null=True, verbose_name="Remarks")
    adjusted = models.BooleanField(default=False, verbose_name="Stock Adjusted")
    
    class Meta:
        verbose_name_plural = '7.2.1 Stock Audit Items'
        unique_together = ('audit', 'product')
    
    def __str__(self):
        return f"{self.product.name}: System={self.system_qty}, Physical={self.physical_qty or '?'}, Variance={self.variance}"
    
    def variance_display(self):
        """Display variance quantity with brackets for negative"""
        if self.variance < 0:
            return f"({abs(self.variance):,.0f})"
        elif self.variance > 0:
            return f"{self.variance:+,.0f}"
        return "0"
    
    def variance_value_display(self):
        """Display variance value with brackets for negative"""
        if self.variance_value < 0:
            return f"Rs. ({abs(self.variance_value):,.2f})"
        elif self.variance_value > 0:
            return f"Rs. {self.variance_value:,.2f}"
        return "Rs. 0.00"
    
    def save(self, *args, **kwargs):
        if not self.unit and self.product.unit:
            self.unit = self.product.unit.name
        
        # Get latest price from inventory
        if not self.price or self.price == 0:
            batches = StockBatch.objects.filter(product=self.product, warehouse=self.audit.warehouse)
            if batches.exists():
                self.price = batches.first().price
        
        # Calculate variance
        if self.physical_qty is not None:
            self.variance = self.physical_qty - self.system_qty
            # ✅ FIX: abs() hataya - variance_value ab signed hai
            self.variance_value = Decimal(str(self.variance)) * self.price
        
        super().save(*args, **kwargs)



