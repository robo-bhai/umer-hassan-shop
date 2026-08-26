from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Sale, Purchase, MonthlyClosing, Inventory,Vendor, Customer, GroupSummary
from django.db.models import Sum, F, DecimalField
from datetime import date

def update_group_summary():
    """Update GroupSummary totals."""
    summary, created = GroupSummary.objects.get_or_create()
    summary.calculate_totals()

# Signal for Vendor Save and Delete
@receiver(post_save, sender=Vendor)

def update_vendor_summary(sender, instance, **kwargs):
    update_group_summary()

# Signal for Customer Save and Delete
@receiver(post_save, sender=Customer)

def update_customer_summary(sender, instance, **kwargs):
    update_group_summary()
