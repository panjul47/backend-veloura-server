"""
Views untuk Veloura Visual API

Mencakup materi:
1. Query Dasar ORM (CRUD)
2. Query Relasional (ForeignKey, select_related, prefetch_related)
3. Aggregate & Annotate (Count, Max, Min, Avg)
4. Optimasi ORM (select_related, prefetch_related, bulk_create)
5. Statistik Course/Booking & User
"""

from django.http import JsonResponse
from django.contrib.auth.models import User
from django.core import serializers
from django.db.models import Max, Min, Avg, Count, Q, Sum
from core.models import Package, PackageFeature, Booking, Photographer, Gallery, Review


# ─── TESTING / QUERY DASAR ────────────────────────────────────────────────────

def testing(request):
    """
    Demonstrasi query dasar ORM:
    - create_user
    - filter + exists
    - get (pk)
    - delete
    - serialize
    """
    user_test = User.objects.filter(username="usertesting")

    if not user_test.exists():
        user_test = User.objects.create_user(
            username="usertesting",
            email="usertest@veloura.com",
            password="sanditesting"
        )

    all_users  = serializers.serialize('python', User.objects.all())
    admin      = User.objects.get(pk=1)
    user_test.delete()
    after_del  = serializers.serialize('python', User.objects.all())

    return JsonResponse({
        "admin_user":   serializers.serialize('python', [admin])[0],
        "all_users":    all_users,
        "after_delete": after_del,
    })


# ─── PAKET ────────────────────────────────────────────────────────────────────

def all_packages(request):
    """
    Select all packages dengan fitur-fiturnya.
    Optimasi: prefetch_related untuk menghindari N+1 pada features.
    """
    # ✅ prefetch_related — ambil semua features sekaligus (1 query tambahan)
    packages = Package.objects.prefetch_related('features').all()

    result = []
    for pkg in packages:
        result.append({
            'id':           pkg.id,
            'name':         pkg.name,
            'description':  pkg.description,
            'price':        pkg.price,
            'duration':     pkg.duration,
            'type':         pkg.get_package_type_display(),
            'tier':         pkg.get_package_tier_display(),
            'is_featured':  pkg.is_featured,
            # prefetch_related memastikan ini tidak trigger query baru per paket
            'features':     [f.description for f in pkg.features.all()],
        })

    return JsonResponse(result, safe=False)


def package_stat(request):
    """
    Statistik paket menggunakan aggregate & annotate.
    Materi: Max, Min, Avg, Count, annotate booking_count
    """
    packages = Package.objects.all()

    stats = packages.aggregate(
        max_price=Max('price'),
        min_price=Min('price'),
        avg_price=Avg('price'),
    )

    # annotate: hitung jumlah booking per paket
    packages_with_count = Package.objects.annotate(
        booking_count=Count('bookings')
    ).order_by('-booking_count')

    most_booked = packages_with_count.first()
    least_booked = packages_with_count.last()

    return JsonResponse({
        'total_packages': packages.count(),
        'price_stats':    stats,
        'most_booked':    {
            'id': most_booked.id,
            'name': most_booked.name,
            'booking_count': most_booked.booking_count,
        } if most_booked else None,
        'least_booked':   {
            'id': least_booked.id,
            'name': least_booked.name,
            'booking_count': least_booked.booking_count,
        } if least_booked else None,
    })


# ─── BOOKING ──────────────────────────────────────────────────────────────────

def all_bookings(request):
    """
    Select semua booking dengan data relasi client & package.
    Optimasi: select_related untuk ForeignKey (JOIN dalam 1 query)
    """
    # ✅ select_related — JOIN client + package + photographer dalam 1 query SQL
    bookings = Booking.objects.select_related(
        'client', 'package', 'photographer__user'
    ).all()

    result = []
    for b in bookings:
        result.append({
            'id':          b.id,
            'event_type':  b.get_event_type_display(),
            'event_date':  str(b.event_date),
            'location':    b.location,
            'status':      b.get_status_display(),
            'total_price': b.total_price,
            # select_related: tidak ada query tambahan di sini
            'client': {
                'id':       b.client.id,
                'username': b.client.username,
                'email':    b.client.email,
                'fullname': f"{b.client.first_name} {b.client.last_name}".strip(),
            },
            'package': {
                'id':    b.package.id,
                'name':  b.package.name,
                'price': b.package.price,
                'type':  b.package.get_package_type_display(),
            },
            'photographer': {
                'name': b.photographer.user.get_full_name() or b.photographer.user.username,
                'spec': b.photographer.get_specialization_display(),
            } if b.photographer else None,
        })

    return JsonResponse(result, safe=False)


def booking_stat(request):
    """
    Statistik semua booking:
    - Jumlah total booking
    - Booking per status
    - Total revenue
    - Booking per event type
    - Paket paling populer
    Materi: aggregate, annotate, Count, Sum, filter
    """
    bookings = Booking.objects.all()

    # Aggregate: total revenue dari booking yang selesai
    revenue = bookings.filter(status='done').aggregate(
        total=Sum('total_price'),
        avg=Avg('total_price'),
    )

    # Annotate: jumlah booking per status
    status_counts = {}
    for status_code, status_label in Booking._meta.get_field('status').choices:
        status_counts[status_label] = bookings.filter(status=status_code).count()

    # Paket paling populer (annotate + order_by)
    popular_packages = Package.objects.annotate(
        booking_count=Count('bookings')
    ).order_by('-booking_count')[:3]

    # Booking per event type
    event_counts = {}
    for code, label in Booking._meta.get_field('event_type').choices:
        event_counts[label] = bookings.filter(event_type=code).count()

    return JsonResponse({
        'total_bookings':   bookings.count(),
        'status_breakdown': status_counts,
        'event_breakdown':  event_counts,
        'revenue': {
            'total': revenue['total'] or 0,
            'avg':   round(revenue['avg'] or 0, 2),
        },
        'popular_packages': [
            {'name': p.name, 'type': p.get_package_type_display(), 'bookings': p.booking_count}
            for p in popular_packages
        ],
    })


def booking_detail(request, booking_id):
    """
    Detail satu booking dengan semua relasi.
    Materi: select_related + prefetch_related kombinasi
    """
    try:
        # select_related untuk FK langsung, prefetch untuk reverse relation
        booking = Booking.objects.select_related(
            'client', 'package', 'photographer__user'
        ).prefetch_related(
            'gallery_items'
        ).get(pk=booking_id)
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking tidak ditemukan'}, status=404)

    # Cek apakah ada review (OneToOne)
    try:
        review = {
            'rating':  booking.review.rating,
            'comment': booking.review.comment,
        }
    except Review.DoesNotExist:
        review = None

    return JsonResponse({
        'id':          booking.id,
        'event_type':  booking.get_event_type_display(),
        'event_date':  str(booking.event_date),
        'location':    booking.location,
        'notes':       booking.notes,
        'status':      booking.get_status_display(),
        'total_price': booking.total_price,
        'client': {
            'id':       booking.client.id,
            'username': booking.client.username,
            'email':    booking.client.email,
            'fullname': f"{booking.client.first_name} {booking.client.last_name}".strip(),
        },
        'package': {
            'id':       booking.package.id,
            'name':     booking.package.name,
            'price':    booking.package.price,
            'duration': booking.package.duration,
            'type':     booking.package.get_package_type_display(),
        },
        'photographer': {
            'name': booking.photographer.user.get_full_name() or booking.photographer.user.username,
            'spec': booking.photographer.get_specialization_display(),
        } if booking.photographer else None,
        # prefetch_related: tidak ada query tambahan
        'gallery_count': booking.gallery_items.count(),
        'gallery': [
            {'id': g.id, 'title': g.title, 'image_url': g.image_url}
            for g in booking.gallery_items.all()
        ],
        'review': review,
    })


# ─── USER / KLIEN ─────────────────────────────────────────────────────────────

def user_stat(request):
    """
    Statistik semua user:
    - Total user non-admin
    - User yang pernah booking
    - User yang belum pernah booking
    - Rata-rata booking per user
    - Top klien (booking terbanyak)
    Materi: annotate, filter, aggregate, Q object
    """
    # Semua user non-admin
    non_admin = User.objects.filter(is_superuser=False)

    # User yang pernah booking (annotate + filter)
    users_with_booking = non_admin.annotate(
        booking_count=Count('bookings')
    ).filter(booking_count__gt=0)

    # User yang belum pernah booking
    users_no_booking = non_admin.annotate(
        booking_count=Count('bookings')
    ).filter(booking_count=0)

    # Rata-rata booking per user
    avg_booking = non_admin.annotate(
        booking_count=Count('bookings')
    ).aggregate(avg=Avg('booking_count'))

    # Top 5 klien
    top_clients = non_admin.annotate(
        booking_count=Count('bookings'),
        total_spent=Sum('bookings__total_price'),
    ).filter(booking_count__gt=0).order_by('-booking_count')[:5]

    return JsonResponse({
        'total_non_admin':       non_admin.count(),
        'users_with_booking':    users_with_booking.count(),
        'users_no_booking':      users_no_booking.count(),
        'avg_booking_per_user':  round(avg_booking['avg'] or 0, 2),
        'top_clients': [
            {
                'id':            u.id,
                'username':      u.username,
                'email':         u.email,
                'booking_count': u.booking_count,
                'total_spent':   u.total_spent or 0,
            }
            for u in top_clients
        ],
        'users_no_booking_list': [
            {'id': u.id, 'username': u.username, 'email': u.email}
            for u in users_no_booking
        ],
    }, safe=False)


def user_detail(request, user_id):
    """
    Detail statistik satu user:
    - Jumlah booking per status
    - Total pengeluaran
    - Paket favorit
    - Review yang pernah ditulis
    Materi: select_related, prefetch_related, annotate, filter
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User tidak ditemukan'}, status=404)

    # Semua booking user dengan relasi (select_related)
    bookings = Booking.objects.select_related('package').filter(client=user)

    # Aggregate
    stats = bookings.aggregate(
        total_spent=Sum('total_price'),
        total_bookings=Count('id'),
    )

    # Paket favorit (paling sering dipesan)
    fav_package = bookings.values(
        'package__name', 'package__package_type'
    ).annotate(count=Count('id')).order_by('-count').first()

    # Booking per status
    status_breakdown = {}
    for code, label in Booking._meta.get_field('status').choices:
        status_breakdown[label] = bookings.filter(status=code).count()

    return JsonResponse({
        'id':               user.id,
        'username':         user.username,
        'email':            user.email,
        'fullname':         f"{user.first_name} {user.last_name}".strip(),
        'total_bookings':   stats['total_bookings'] or 0,
        'total_spent':      stats['total_spent'] or 0,
        'status_breakdown': status_breakdown,
        'favorite_package': {
            'name':  fav_package['package__name'],
            'type':  fav_package['package__package_type'],
            'count': fav_package['count'],
        } if fav_package else None,
    })


# ─── FOTOGRAFER ───────────────────────────────────────────────────────────────

def photographer_stat(request):
    """
    Statistik fotografer:
    - Total fotografer
    - Fotografer tersibuk (booking terbanyak)
    - Rating rata-rata per fotografer
    Materi: select_related (OneToOne), annotate, Avg
    """
    # select_related untuk OneToOne ke User
    photographers = Photographer.objects.select_related('user').annotate(
        booking_count=Count('bookings'),
        avg_rating=Avg('bookings__review__rating'),
    ).order_by('-booking_count')

    return JsonResponse({
        'total_photographers': photographers.count(),
        'photographers': [
            {
                'id':            p.id,
                'name':          p.user.get_full_name() or p.user.username,
                'specialization': p.get_specialization_display(),
                'is_available':  p.is_available,
                'booking_count': p.booking_count,
                'avg_rating':    round(p.avg_rating or 0, 2),
            }
            for p in photographers
        ],
    }, safe=False)


# ─── REVIEW ───────────────────────────────────────────────────────────────────

def public_reviews(request):
    """
    Semua review publik dengan data klien dan paket.
    Materi: select_related multi-level (review -> booking -> client/package)
    """
    # select_related multi-level: review -> booking -> client & package
    reviews = Review.objects.select_related(
        'booking__client',
        'booking__package',
    ).filter(is_public=True).order_by('-created_at')

    result = []
    for r in reviews:
        result.append({
            'id':      r.id,
            'rating':  r.rating,
            'comment': r.comment,
            'photo':   request.build_absolute_uri(r.photo.url) if r.photo else None,
            'date':    str(r.created_at.date()),
            'client': {
                'username': r.booking.client.username,
                'fullname': f"{r.booking.client.first_name} {r.booking.client.last_name}".strip(),
            },
            'package': {
                'name': r.booking.package.name,
                'type': r.booking.package.get_package_type_display(),
            },
        })

    return JsonResponse(result, safe=False)


def review_stat(request):
    """
    Statistik review:
    - Rata-rata rating keseluruhan
    - Distribusi rating (1-5)
    - Rating per tipe paket
    Materi: aggregate, annotate, values + annotate
    """
    reviews = Review.objects.filter(is_public=True)

    overall = reviews.aggregate(
        avg_rating=Avg('rating'),
        total=Count('id'),
    )

    # Distribusi rating
    distribution = {}
    for i in range(1, 6):
        distribution[f'{i}_star'] = reviews.filter(rating=i).count()

    # Rating per tipe paket
    by_type = reviews.values(
        'booking__package__package_type'
    ).annotate(
        avg=Avg('rating'),
        count=Count('id'),
    )

    return JsonResponse({
        'overall_avg':  round(overall['avg_rating'] or 0, 2),
        'total_reviews': overall['total'],
        'distribution': distribution,
        'by_package_type': [
            {
                'type':  item['booking__package__package_type'],
                'avg':   round(item['avg'], 2),
                'count': item['count'],
            }
            for item in by_type
        ],
    })
