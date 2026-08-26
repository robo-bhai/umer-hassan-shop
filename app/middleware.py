from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from .models import License
from datetime import date

class LicenseMiddleware(MiddlewareMixin):
    """
    Middleware to check license validity and auto-deactivate on expiry.
    """

    def process_request(self, request):
        # Allow access to admin and static/license pages
        allowed_paths = [
            reverse('admin:login'),
            reverse('admin:logout'),
            '/admin/', '/admin/license/', '/admin/license/license/',
        ]
        if any(request.path.startswith(path) for path in allowed_paths):
            return None

        license = License.objects.first()

        if not license:
            return self._license_error("❌ License not found!")

        if license.expiry_date < date.today():
            if license.is_active:
                license.is_active = False
                license.save(update_fields=['is_active'])
            return self._license_error("⚠️ License expired and deactivated!")

        if not license.is_active:
            return self._license_error("⚠️ License is inactive. Please renew.")

        return None

    def _license_error(self, message):
        return HttpResponseRedirect(f"/license-expired/?msg={message}")
