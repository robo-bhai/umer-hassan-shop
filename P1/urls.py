from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/find-product-by-barcode/', views.find_product_by_barcode, name='find_product_by_barcode'),
    path('', include('app.urls')),
    
    # Service worker at root level
    path('service-worker.js', TemplateView.as_view(
        template_name='app/service-worker.js',
        content_type='application/javascript'
    ), name='service_worker_root'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


#from django.contrib import admin
#from django.urls import path, include

#urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/find-product-by-barcode/', views.find_product_by_barcode, name='find_product_by_barcode'),
    path('app/', include('app.urls')),  # Ensure this line exists
#]
