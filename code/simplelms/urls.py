"""
URL Configuration — Veloura Visual

Production:
  - Hanya /admin/, /api/v1/, dan /media/ yang terbuka
  - /silk/ dan legacy endpoints hanya aktif saat DEBUG=True

API Docs (development only):
  http://localhost:8001/api/v1/docs
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.apiv1 import apiv1

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── Django Ninja REST API ─────────────────────────────────────────────────
    path('api/v1/', apiv1.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ── Development only ──────────────────────────────────────────────────────────
# Silk profiler dan legacy endpoints hanya aktif saat DEBUG=True
if settings.DEBUG:
    from core.views import (
        testing,
        all_packages, package_stat,
        all_bookings, booking_stat, booking_detail,
        user_stat, user_detail,
        photographer_stat,
        public_reviews, review_stat,
    )

    urlpatterns += [
        path('silk/', include('silk.urls', namespace='silk')),

        # Legacy views — hanya untuk development/testing
        path('testing/',                         testing),
        path('packages/',                        all_packages),
        path('package-stats/',                   package_stat),
        path('bookings/',                        all_bookings),
        path('booking-stats/',                   booking_stat),
        path('booking-detail/<int:booking_id>/', booking_detail),
        path('user-stats/',                      user_stat),
        path('user-detail/<int:user_id>/',       user_detail),
        path('photographer-stats/',              photographer_stat),
        path('reviews/',                         public_reviews),
        path('review-stats/',                    review_stat),
    ]
