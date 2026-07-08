"""
REST API Veloura Visual — Django Ninja + JWT + Throttling + Pagination + Filtering

Throttling:
  - Anonymous : 30 request/menit
  - Authenticated: 200 request/menit
  - Endpoint sensitif (register, create): 5 request/menit per user

Pagination:
  - GET /packages/     → page_size=10, query: ?page=1
  - GET /bookings/     → page_size=10, query: ?page=1
  - GET /reviews/      → page_size=10, query: ?page=1

Filtering:
  - GET /packages/     → ?search=&price_gte=&price_lte=&package_type=&is_featured=
  - GET /bookings/     → ?status=&event_type=&search=
  - GET /reviews/      → ?rating_gte=&search=

Endpoint publik:
  GET  /api/v1/packages/                  — Semua paket (paginated + filtered)
  GET  /api/v1/packages/{id}/             — Detail paket
  GET  /api/v1/package-stats/             — Statistik paket
  GET  /api/v1/bookings/                  — Semua booking (paginated + filtered)
  GET  /api/v1/bookings/{id}/             — Detail booking
  GET  /api/v1/booking-stats/             — Statistik booking
  GET  /api/v1/reviews/                   — Review publik (paginated + filtered)
  GET  /api/v1/review-stats/              — Statistik review
  GET  /api/v1/photographers/             — Statistik fotografer
  POST /api/v1/register/                  — Registrasi user baru

Endpoint auth (butuh JWT):
  POST /api/v1/auth/sign-in/              — Login
  POST /api/v1/auth/token-refresh/        — Refresh token
  GET  /api/v1/me/                        — Profil user login
  GET  /api/v1/my-bookings/              — Booking milik user login
  POST /api/v1/bookings/create/           — Buat booking
  POST /api/v1/reviews/create/            — Tulis review
"""

from ninja import NinjaAPI, Schema, Query
from ninja.errors import HttpError, ValidationError
from ninja.throttling import AnonRateThrottle, AuthRateThrottle, UserRateThrottle
from ninja.filter_schema import FilterSchema
from ninja_simple_jwt.auth.views.api import mobile_auth_router
from ninja_simple_jwt.auth.ninja_auth import HttpJwtAuth
from pydantic import validator, Field
from django.contrib.auth.models import User
from django.db.models import Max, Min, Avg, Count, Sum, Q
from django.conf import settings
from typing import Optional, List
import re
import logging

from core.models import Package, Booking, Photographer, Review

logger = logging.getLogger(__name__)

# ─── THROTTLING GLOBAL ────────────────────────────────────────────────────────

apiv1 = NinjaAPI(
    title="Veloura Visual API",
    description="REST API untuk sistem manajemen fotografi Veloura Visual",
    version="1.0.0",
    # Docs tetap aktif tapi bisa diakses — tidak menyebabkan masalah security signifikan
    # karena semua endpoint sensitif dilindungi JWT
    throttle=[
        AnonRateThrottle('30/m'),
        AuthRateThrottle('200/m'),
    ],
)

apiv1.add_router("/auth/", mobile_auth_router)
apiAuth = HttpJwtAuth()


# ─── EXCEPTION HANDLERS ───────────────────────────────────────────────────────
# Di production, semua 500 error hanya return pesan generik
# Detail error di-log ke file, tidak dikirim ke client

@apiv1.exception_handler(Exception)
def generic_exception_handler(request, exc):
    """Tangkap semua unhandled exception, log ke file, return pesan generik"""
    from django.http import JsonResponse
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method, request.path, exc,
        exc_info=True,
    )
    if settings.DEBUG:
        raise exc  # Di development, tetap tampilkan traceback
    return JsonResponse(
        {"detail": "Terjadi kesalahan server. Silakan coba lagi."},
        status=500,
    )


# ─── SCHEMA OUTPUT ────────────────────────────────────────────────────────────

class PackageOut(Schema):
    id: int
    name: str
    description: str
    price: int
    duration: str
    package_type: str
    package_tier: str
    is_featured: bool


class PackageDetailOut(PackageOut):
    features: List[str]


class ClientOut(Schema):
    id: int
    username: str
    email: str
    fullname: str


class PhotographerOut(Schema):
    name: str
    specialization: str


class BookingOut(Schema):
    id: int
    event_type: str
    event_date: str
    location: str
    status: str
    total_price: int
    client: ClientOut
    package: PackageOut
    photographer: Optional[PhotographerOut]


class ReviewOut(Schema):
    id: int
    rating: int
    comment: str
    photo: Optional[str]
    date: str
    client_username: str
    client_fullname: str
    package_name: str
    package_type: str


class UserOut(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str


# ─── SCHEMA INPUT ─────────────────────────────────────────────────────────────

class Register(Schema):
    """Schema registrasi dengan validasi username, password, email"""
    username: str
    password: str
    email: str
    first_name: str
    last_name: str

    @validator("username")
    def validate_username(cls, value):
        if len(value) < 5:
            raise ValueError("Username harus lebih dari 5 karakter")
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise ValueError("Username hanya boleh huruf, angka, dan underscore")
        return value

    @validator("password")
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password harus lebih dari 8 karakter")
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d).+$', value):
            raise ValueError("Password harus mengandung huruf dan angka")
        return value

    @validator("email")
    def validate_email(cls, value):
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', value):
            raise ValueError("Format email tidak valid")
        return value


class BookingCreate(Schema):
    """Schema untuk membuat booking baru"""
    package_id: int
    event_type: str
    event_date: str
    location: str
    notes: str = ""

    @validator("event_type")
    def validate_event_type(cls, value):
        valid = ['wedding', 'graduation', 'birthday', 'corporate', 'daily', 'other']
        if value not in valid:
            raise ValueError(f"event_type harus salah satu dari: {', '.join(valid)}")
        return value

    @validator("location")
    def validate_location(cls, value):
        if len(value.strip()) < 5:
            raise ValueError("Lokasi harus lebih dari 5 karakter")
        return value


class ReviewCreate(Schema):
    """Schema untuk menulis review"""
    booking_id: int
    rating: int
    comment: str

    @validator("rating")
    def validate_rating(cls, value):
        if value < 1 or value > 5:
            raise ValueError("Rating harus antara 1 sampai 5")
        return value

    @validator("comment")
    def validate_comment(cls, value):
        if len(value.strip()) < 10:
            raise ValueError("Komentar harus lebih dari 10 karakter")
        return value


# ─── FILTER SCHEMA ────────────────────────────────────────────────────────────

class PackageFilter(FilterSchema):
    """
    Filter untuk endpoint GET /packages/
    Contoh: /api/v1/packages/?price_gte=500000&package_type=harian&search=basic
    """
    price_gte:    Optional[int]  = Field(None, description="Harga minimum")
    price_lte:    Optional[int]  = Field(None, description="Harga maksimum")
    package_type: Optional[str]  = Field(None, description="Tipe paket: harian / event")
    package_tier: Optional[str]  = Field(None, description="Tier: basic / standard / premium")
    is_featured:  Optional[bool] = Field(None, description="Hanya paket unggulan")
    search:       Optional[str]  = Field(
        None, q=['name__icontains', 'description__icontains'],
        description="Cari berdasarkan nama atau deskripsi"
    )

    def filter_price_gte(self, value: int):
        return Q(price__gte=value) if value is not None else Q()

    def filter_price_lte(self, value: int):
        return Q(price__lte=value) if value is not None else Q()

    def filter_package_type(self, value: str):
        return Q(package_type__iexact=value) if value else Q()

    def filter_package_tier(self, value: str):
        return Q(package_tier__iexact=value) if value else Q()

    def filter_is_featured(self, value: bool):
        return Q(is_featured=value) if value is not None else Q()


class BookingFilter(FilterSchema):
    """
    Filter untuk endpoint GET /bookings/
    Contoh: /api/v1/bookings/?status=pending&event_type=wedding
    """
    status:     Optional[str] = Field(None, description="Status booking")
    event_type: Optional[str] = Field(None, description="Jenis acara")
    search:     Optional[str] = Field(
        None, q=['location__icontains', 'notes__icontains', 'client__username__icontains'],
        description="Cari berdasarkan lokasi, catatan, atau username klien"
    )

    def filter_status(self, value: str):
        return Q(status__iexact=value) if value else Q()

    def filter_event_type(self, value: str):
        return Q(event_type__iexact=value) if value else Q()


class ReviewFilter(FilterSchema):
    """
    Filter untuk endpoint GET /reviews/
    Contoh: /api/v1/reviews/?rating_gte=4&search=bagus
    """
    rating_gte: Optional[int] = Field(None, description="Rating minimum (1-5)")
    rating_lte: Optional[int] = Field(None, description="Rating maksimum (1-5)")
    search:     Optional[str] = Field(
        None, q=['comment__icontains', 'booking__client__username__icontains'],
        description="Cari berdasarkan komentar atau username"
    )

    def filter_rating_gte(self, value: int):
        return Q(rating__gte=value) if value is not None else Q()

    def filter_rating_lte(self, value: int):
        return Q(rating__lte=value) if value is not None else Q()


# ─── ENDPOINTS: PAKET ─────────────────────────────────────────────────────────

def _build_package(pkg):
    return {
        'id':           pkg.id,
        'name':         pkg.name,
        'description':  pkg.description,
        'price':        pkg.price,
        'duration':     pkg.duration,
        'package_type': pkg.get_package_type_display(),
        'package_tier': pkg.get_package_tier_display(),
        'is_featured':  pkg.is_featured,
        'features':     [f.description for f in pkg.features.all()],
    }


@apiv1.get("packages/", response=List[PackageDetailOut], tags=["Paket"])
def get_packages(request, filters: PackageFilter = Query(...), page: int = 1):
    """
    Ambil semua paket fotografi dengan pagination dan filtering.
    - page_size: 10 per halaman
    - Contoh: /api/v1/packages/?page=1&price_gte=300000&search=wedding
    """
    qs     = Package.objects.prefetch_related('features').all()
    qs     = filters.filter(qs)
    total  = qs.count()
    size   = 10
    offset = (page - 1) * size
    items  = qs[offset: offset + size]

    return [_build_package(p) for p in items]


@apiv1.get("packages/{package_id}/", response=PackageDetailOut, tags=["Paket"])
def get_package_detail(request, package_id: int):
    """Detail satu paket berdasarkan ID."""
    try:
        pkg = Package.objects.prefetch_related('features').get(pk=package_id)
    except Package.DoesNotExist:
        raise HttpError(404, "Paket tidak ditemukan")
    return _build_package(pkg)


@apiv1.get("package-stats/", tags=["Paket"])
def get_package_stats(request):
    """Statistik paket: harga max/min/avg dan paket terpopuler."""
    stats = Package.objects.aggregate(
        max_price=Max('price'), min_price=Min('price'), avg_price=Avg('price'),
    )
    packages_with_count = Package.objects.annotate(
        booking_count=Count('bookings')
    ).order_by('-booking_count')
    most_booked  = packages_with_count.first()
    least_booked = packages_with_count.last()

    return {
        'total_packages': Package.objects.count(),
        'price_stats':    stats,
        'most_booked': {
            'id': most_booked.id, 'name': most_booked.name,
            'booking_count': most_booked.booking_count,
        } if most_booked else None,
        'least_booked': {
            'id': least_booked.id, 'name': least_booked.name,
            'booking_count': least_booked.booking_count,
        } if least_booked else None,
    }


# ─── ENDPOINTS: BOOKING ───────────────────────────────────────────────────────

def _build_booking(b):
    return {
        'id':          b.id,
        'event_type':  b.get_event_type_display(),
        'event_date':  str(b.event_date),
        'location':    b.location,
        'status':      b.get_status_display(),
        'total_price': b.total_price,
        'client': {
            'id': b.client.id, 'username': b.client.username,
            'email': b.client.email,
            'fullname': f"{b.client.first_name} {b.client.last_name}".strip(),
        },
        'package': {
            'id': b.package.id, 'name': b.package.name,
            'description': b.package.description, 'price': b.package.price,
            'duration': b.package.duration,
            'package_type': b.package.get_package_type_display(),
            'package_tier': b.package.get_package_tier_display(),
            'is_featured': b.package.is_featured,
        },
        'photographer': {
            'name': b.photographer.user.get_full_name() or b.photographer.user.username,
            'specialization': b.photographer.get_specialization_display(),
        } if b.photographer else None,
    }


@apiv1.get("bookings/", response=List[BookingOut], auth=apiAuth, tags=["Booking"])
def get_bookings(request, filters: BookingFilter = Query(...), page: int = 1):
    """
    Semua booking — hanya bisa diakses oleh user yang sudah login.
    Admin dapat melihat semua booking; user biasa hanya melihat miliknya.
    """
    user = User.objects.get(pk=request.user.id)

    # Superuser/staff bisa lihat semua, user biasa hanya milik sendiri
    if user.is_staff or user.is_superuser:
        qs = Booking.objects.select_related(
            'client', 'package', 'photographer__user'
        ).all()
    else:
        qs = Booking.objects.select_related(
            'client', 'package', 'photographer__user'
        ).filter(client=user)

    qs     = filters.filter(qs)
    size   = 10
    offset = (page - 1) * size
    items  = qs[offset: offset + size]
    return [_build_booking(b) for b in items]


@apiv1.get("bookings/{booking_id}/", auth=apiAuth, tags=["Booking"])
def get_booking_detail(request, booking_id: int):
    """Detail booking — hanya bisa diakses oleh pemilik booking atau admin."""
    user = User.objects.get(pk=request.user.id)
    try:
        # User biasa hanya bisa akses booking miliknya
        if user.is_staff or user.is_superuser:
            booking = Booking.objects.select_related(
                'client', 'package', 'photographer__user'
            ).prefetch_related('gallery_items').get(pk=booking_id)
        else:
            booking = Booking.objects.select_related(
                'client', 'package', 'photographer__user'
            ).prefetch_related('gallery_items').get(pk=booking_id, client=user)
    except Booking.DoesNotExist:
        raise HttpError(404, "Booking tidak ditemukan")

    try:
        review = {'rating': booking.review.rating, 'comment': booking.review.comment}
    except Review.DoesNotExist:
        review = None

    return {
        **_build_booking(booking),
        'notes': booking.notes,
        'gallery_count': booking.gallery_items.count(),
        'gallery': [
            {'id': g.id, 'title': g.title, 'image_url': g.image_url}
            for g in booking.gallery_items.all()
        ],
        'review': review,
    }


@apiv1.get("booking-stats/", auth=apiAuth, tags=["Booking"])
def get_booking_stats(request):
    """Statistik booking: revenue, breakdown status & event type."""
    bookings = Booking.objects.all()
    revenue  = bookings.filter(status='done').aggregate(
        total=Sum('total_price'), avg=Avg('total_price')
    )
    status_counts = {
        label: bookings.filter(status=code).count()
        for code, label in Booking._meta.get_field('status').choices
    }
    event_counts = {
        label: bookings.filter(event_type=code).count()
        for code, label in Booking._meta.get_field('event_type').choices
    }
    popular_packages = Package.objects.annotate(
        booking_count=Count('bookings')
    ).order_by('-booking_count')[:3]

    return {
        'total_bookings':   bookings.count(),
        'status_breakdown': status_counts,
        'event_breakdown':  event_counts,
        'revenue': {'total': revenue['total'] or 0, 'avg': round(revenue['avg'] or 0, 2)},
        'popular_packages': [
            {'name': p.name, 'type': p.get_package_type_display(), 'bookings': p.booking_count}
            for p in popular_packages
        ],
    }


class BookingCreatePublic(Schema):
    """Schema booking tanpa JWT — gunakan username untuk identify client"""
    username: str
    package_id: int
    event_type: str
    event_date: str
    location: str
    notes: str = ""

    @validator("event_type")
    def validate_event_type(cls, value):
        valid = ['wedding', 'graduation', 'birthday', 'corporate', 'daily', 'other']
        if value not in valid:
            raise ValueError(f"event_type harus salah satu dari: {', '.join(valid)}")
        return value

    @validator("location")
    def validate_location(cls, value):
        if len(value.strip()) < 5:
            raise ValueError("Lokasi harus lebih dari 5 karakter")
        return value


@apiv1.post("book/", tags=["Booking"])
def create_booking_public(request, data: BookingCreatePublic):
    """
    Buat booking — identifikasi user dari username di body request.
    Tidak memerlukan JWT token.
    """
    try:
        client = User.objects.get(username=data.username)
    except User.DoesNotExist:
        raise HttpError(404, "User tidak ditemukan. Silakan register terlebih dahulu.")

    try:
        package = Package.objects.get(pk=data.package_id)
    except Package.DoesNotExist:
        raise HttpError(404, "Paket tidak ditemukan")

    booking = Booking.objects.create(
        client=client, package=package,
        event_type=data.event_type, event_date=data.event_date,
        location=data.location, notes=data.notes,
    )
    return {
        'id': booking.id, 'status': booking.get_status_display(),
        'total_price': booking.total_price, 'event_date': str(booking.event_date),
        'package': package.name, 'client': client.username,
        'message': "Booking berhasil dibuat",
    }


@apiv1.post("create-booking/", auth=apiAuth, tags=["Booking"],
            throttle=[UserRateThrottle('5/m')])
def create_booking(request, data: BookingCreate):
    """
    Buat booking baru. Harus login (JWT).
    Throttle: maksimal 5 booking per menit per user.
    """
    try:
        package = Package.objects.get(pk=data.package_id)
    except Package.DoesNotExist:
        raise HttpError(404, "Paket tidak ditemukan")

    client  = User.objects.get(pk=request.user.id)
    booking = Booking.objects.create(
        client=client, package=package,
        event_type=data.event_type, event_date=data.event_date,
        location=data.location, notes=data.notes,
    )
    return {
        'id': booking.id, 'status': booking.get_status_display(),
        'total_price': booking.total_price, 'event_date': str(booking.event_date),
        'package': package.name, 'client': client.username,
        'message': "Booking berhasil dibuat",
    }


# ─── ENDPOINTS: FOTOGRAFER ────────────────────────────────────────────────────

@apiv1.get("photographers/", auth=apiAuth, tags=["Fotografer"])
def get_photographers(request):
    """Statistik fotografer dengan booking count dan rata-rata rating."""
    photographers = Photographer.objects.select_related('user').annotate(
        booking_count=Count('bookings'),
        avg_rating=Avg('bookings__review__rating'),
    ).order_by('-booking_count')

    return {
        'total_photographers': photographers.count(),
        'photographers': [
            {
                'id': p.id,
                'name': p.user.get_full_name() or p.user.username,
                'specialization': p.get_specialization_display(),
                'is_available': p.is_available,
                'booking_count': p.booking_count,
                'avg_rating': round(p.avg_rating or 0, 2),
            }
            for p in photographers
        ],
    }


# ─── ENDPOINTS: REVIEW ────────────────────────────────────────────────────────

@apiv1.get("reviews/", response=List[ReviewOut], tags=["Review"])
def get_reviews(request, filters: ReviewFilter = Query(...), page: int = 1):
    """
    Review publik dengan pagination dan filtering.
    - Contoh: /api/v1/reviews/?page=1&rating_gte=4&search=bagus
    """
    qs = Review.objects.select_related(
        'booking__client', 'booking__package',
    ).filter(is_public=True).order_by('-created_at')
    qs     = filters.filter(qs)
    size   = 10
    offset = (page - 1) * size
    items  = qs[offset: offset + size]

    return [
        {
            'id':              r.id,
            'rating':          r.rating,
            'comment':         r.comment,
            'photo':           request.build_absolute_uri(r.photo.url) if r.photo else None,
            'date':            str(r.created_at.date()),
            'client_username': r.booking.client.username,
            'client_fullname': f"{r.booking.client.first_name} {r.booking.client.last_name}".strip(),
            'package_name':    r.booking.package.name,
            'package_type':    r.booking.package.get_package_type_display(),
        }
        for r in items
    ]


@apiv1.get("review-stats/", tags=["Review"])
def get_review_stats(request):
    """Statistik review: rata-rata, distribusi, per tipe paket."""
    reviews     = Review.objects.filter(is_public=True)
    overall     = reviews.aggregate(avg_rating=Avg('rating'), total=Count('id'))
    distribution = {f'{i}_star': reviews.filter(rating=i).count() for i in range(1, 6)}
    by_type     = reviews.values('booking__package__package_type').annotate(
        avg=Avg('rating'), count=Count('id')
    )
    return {
        'overall_avg':    round(overall['avg_rating'] or 0, 2),
        'total_reviews':  overall['total'],
        'distribution':   distribution,
        'by_package_type': [
            {'type': item['booking__package__package_type'],
             'avg': round(item['avg'], 2), 'count': item['count']}
            for item in by_type
        ],
    }


# ─── ENDPOINTS: AUTH ──────────────────────────────────────────────────────────

@apiv1.post("register/", response=UserOut, tags=["Auth"],
            throttle=[AnonRateThrottle('5/m')])
def register(request, data: Register):
    """
    Registrasi user baru.
    Throttle: maksimal 5 registrasi per menit dari IP yang sama.
    """
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah digunakan")
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email sudah terdaftar")

    new_user = User.objects.create_user(
        username=data.username, password=data.password,
        email=data.email, first_name=data.first_name, last_name=data.last_name,
    )
    return new_user


# ─── ENDPOINTS: AUTH - PROTECTED ─────────────────────────────────────────────

@apiv1.get("me/", auth=apiAuth, tags=["Auth - Protected"])
def get_me(request):
    """Profil user yang sedang login beserta statistik booking."""
    user  = User.objects.get(pk=request.user.id)
    stats = Booking.objects.filter(client=user).aggregate(
        total_bookings=Count('id'), total_spent=Sum('total_price'),
    )
    return {
        'id': user.id, 'username': user.username,
        'email': user.email,
        'fullname': f"{user.first_name} {user.last_name}".strip(),
        'total_bookings': stats['total_bookings'] or 0,
        'total_spent':    stats['total_spent'] or 0,
    }


@apiv1.get("my-bookings/", auth=apiAuth, response=List[BookingOut], tags=["Auth - Protected"])
def get_my_bookings(request, filters: BookingFilter = Query(...), page: int = 1):
    """
    Booking milik user yang login, dengan pagination dan filtering.
    - Contoh: /api/v1/my-bookings/?page=1&status=pending
    """
    user   = User.objects.get(pk=request.user.id)
    qs     = Booking.objects.select_related(
        'package', 'photographer__user', 'client'
    ).filter(client=user).order_by('-event_date')
    qs     = filters.filter(qs)
    size   = 10
    offset = (page - 1) * size
    items  = qs[offset: offset + size]
    return [_build_booking(b) for b in items]


@apiv1.post("create-review/", auth=apiAuth, tags=["Auth - Protected"],
            throttle=[UserRateThrottle('10/m')])
def create_review(request, data: ReviewCreate):
    """
    Tulis review untuk booking yang sudah selesai (status: done).
    Throttle: maksimal 10 review per menit per user.
    """
    user = User.objects.get(pk=request.user.id)

    try:
        booking = Booking.objects.get(pk=data.booking_id, client=user)
    except Booking.DoesNotExist:
        raise HttpError(404, "Booking tidak ditemukan atau bukan milik Anda")

    if booking.status != 'done':
        raise HttpError(400, "Review hanya bisa ditulis untuk booking yang sudah selesai")

    if Review.objects.filter(booking=booking).exists():
        raise HttpError(400, "Booking ini sudah memiliki review")

    review = Review.objects.create(
        booking=booking, rating=data.rating,
        comment=data.comment, is_public=True,
    )
    return {
        'id': review.id, 'booking_id': booking.id,
        'rating': review.rating, 'comment': review.comment,
        'message': "Review berhasil ditambahkan",
    }
