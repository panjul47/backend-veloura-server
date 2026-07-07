"""
Admin configuration untuk Veloura Visual.
Semua model didaftarkan dengan tampilan yang informatif.
Menggunakan django-unfold untuk tampilan yang lebih modern.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from core.models import Package, PackageFeature, Booking, Photographer, Gallery, Review


class PackageFeatureInline(TabularInline):
    model  = PackageFeature
    extra  = 1
    fields = ['description', 'order']


@admin.register(Package)
class PackageAdmin(ModelAdmin):
    list_display   = ['name', 'package_type', 'package_tier', 'price', 'duration', 'is_featured']
    list_filter    = ['package_type', 'package_tier', 'is_featured']
    search_fields  = ['name', 'description']
    inlines        = [PackageFeatureInline]
    ordering       = ['package_type', 'price']


@admin.register(Booking)
class BookingAdmin(ModelAdmin):
    list_display   = ['id', 'client', 'package', 'event_type', 'event_date', 'status', 'total_price']
    list_filter    = ['status', 'event_type', 'package__package_type']
    search_fields  = ['client__username', 'location', 'notes']
    raw_id_fields  = ['client', 'package', 'photographer']
    ordering       = ['-event_date']
    date_hierarchy = 'event_date'


@admin.register(Photographer)
class PhotographerAdmin(ModelAdmin):
    list_display  = ['user', 'specialization', 'is_available']
    list_filter   = ['specialization', 'is_available']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'bio']


class GalleryInline(TabularInline):
    model  = Gallery
    extra  = 0
    fields = ['title', 'image_url', 'file', 'parent']


@admin.register(Gallery)
class GalleryAdmin(ModelAdmin):
    list_display  = ['title', 'booking', 'parent', 'created_at']
    list_filter   = ['booking__package__package_type']
    search_fields = ['title', 'description']
    raw_id_fields = ['booking', 'parent']


@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display  = ['booking', 'rating', 'is_public', 'created_at']
    list_filter   = ['rating', 'is_public']
    search_fields = ['comment', 'booking__client__username']
    ordering      = ['-created_at']
