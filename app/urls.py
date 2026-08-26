from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # Home & Basic
    path('', views.home_view, name='home'),
    path('add-purchase/', views.add_purchase_view, name='add_purchase'),
    path('invoice/<int:sale_id>/', views.generate_invoice_pdf, name='generate_invoice_pdf'),
    
    # ============================================
    # POS URLS
    # ============================================
    path('pos/', views.pos_view, name='pos'),
    path('pos/search-product/', views.pos_search_product, name='pos_search_product'),
    path('pos/quick-add/', views.pos_quick_add, name='pos_quick_add'),
    path('pos/complete-sale/', views.pos_complete_sale, name='pos_complete_sale'),
    path('pos/hold-sale/', views.pos_hold_sale, name='pos_hold_sale'),
    path('pos/print-receipt/<int:sale_id>/', views.pos_print_receipt, name='pos_print_receipt'),
    path('pos/get-cart/', views.pos_get_cart, name='pos_get_cart'),
    path('pos/get-products/', views.pos_get_products, name='pos_get_products'),
    
    # Barcode Search (AJAX)
    path('admin/find-product-by-barcode/', views.find_product_by_barcode, name='find_product_by_barcode'),
    
    # PWA URLs
    path('manifest.json', TemplateView.as_view(
        template_name='app/manifest.json',
        content_type='application/json'
    ), name='manifest'),
    
    path('service-worker.js', TemplateView.as_view(
        template_name='app/service-worker.js',
        content_type='application/javascript'
    ), name='service_worker'),
    
    path('offline/', TemplateView.as_view(
        template_name='app/offline.html'
    ), name='offline'),
]