"""
Importer data dummy untuk Veloura Visual

Materi yang dicakup:
- Import CSV dengan csv.DictReader
- Bulk create dengan bulk_create (optimasi insert massal)
- Penggunaan get_or_create untuk menghindari duplikasi
- Setup Django di luar manage.py
"""

import os
import sys

# Setup path agar bisa import modul Django dari luar project
sys.path.append(os.path.abspath(os.path.join(__file__, *[os.pardir] * 2)))
os.environ['DJANGO_SETTINGS_MODULE'] = 'simplelms.settings'

import django
django.setup()

import csv
from django.contrib.auth.models import User
from core.models import Package, PackageFeature, Booking, Photographer, Review

filepath = './csv_data/'

print("=" * 50)
print("VELOURA VISUAL — DATA IMPORTER")
print("=" * 50)


# ─── 1. IMPORT USER ───────────────────────────────────────────────────────────
print("\n[1/5] Importing users...")

with open(filepath + 'user-data.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    for num, row in enumerate(reader):
        if not User.objects.filter(username=row['username']).exists():
            User.objects.create_user(
                id=num + 2,  # id=1 untuk superuser/admin
                username=row['username'],
                password=row['password'],
                email=row['email'],
                first_name=row['first_name'],
                last_name=row['last_name'],
            )
            print(f"  ✓ User: {row['username']}")
        else:
            print(f"  - Skip (exists): {row['username']}")

print(f"  Total users: {User.objects.count()}")


# ─── 2. IMPORT PAKET ──────────────────────────────────────────────────────────
print("\n[2/5] Importing packages...")

PACKAGE_FEATURES = {
    'Harian Basic':    ['1 Fotografer', '2 Jam Sesi', '15 Foto Edited', '1 Lokasi', 'Pengiriman Online'],
    'Harian Standard': ['1 Fotografer', '4 Jam Sesi', '40 Foto Edited', '2 Lokasi', 'Pengiriman Online', '1 Revisi Editing'],
    'Harian Premium':  ['1 Fotografer', 'Full Day Sesi', '80 Foto Edited', 'Bebas Lokasi', 'Pengiriman Online', '3 Revisi Editing'],
    'Event Basic':     ['1 Fotografer', '3 Jam Coverage', '30 Foto Edited', 'Pengiriman Online'],
    'Event Standard':  ['2 Fotografer', '6 Jam Coverage', '80 Foto Edited', 'Highlight Album', 'Pengiriman Online'],
    'Event Premium':   ['3 Fotografer', 'Full Day Coverage', '150+ Foto Edited', 'Foto + Video', 'Highlight Album', 'Pengiriman Online'],
}

with open(filepath + 'package-data.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    for num, row in enumerate(reader):
        pkg, created = Package.objects.get_or_create(
            name=row['name'],
            defaults={
                'id':           num + 1,
                'description':  row['description'],
                'price':        int(row['price']),
                'duration':     row['duration'],
                'package_type': row['package_type'],
                'package_tier': row['package_tier'],
                'is_featured':  row['is_featured'] == 'True',
            }
        )
        if created:
            # Bulk create fitur paket
            features = PACKAGE_FEATURES.get(pkg.name, [])
            PackageFeature.objects.bulk_create([
                PackageFeature(package=pkg, description=feat, order=i)
                for i, feat in enumerate(features)
            ])
            print(f"  ✓ Package: {pkg.name} ({len(features)} features)")
        else:
            print(f"  - Skip (exists): {pkg.name}")

print(f"  Total packages: {Package.objects.count()}")


# ─── 3. IMPORT FOTOGRAFER ─────────────────────────────────────────────────────
print("\n[3/5] Importing photographers...")

PHOTOGRAPHERS = [
    {'username': 'andi_pratama',  'spec': 'wedding',   'bio': 'Spesialis foto pernikahan dengan 5 tahun pengalaman.'},
    {'username': 'budi_santoso',  'spec': 'portrait',  'bio': 'Fotografer portrait dan fashion.'},
    {'username': 'citra_dewi',    'spec': 'event',     'bio': 'Berpengalaman dalam liputan event besar.'},
]

for data in PHOTOGRAPHERS:
    try:
        user = User.objects.get(username=data['username'])
        _, created = Photographer.objects.get_or_create(
            user=user,
            defaults={
                'specialization': data['spec'],
                'bio':            data['bio'],
                'is_available':   True,
            }
        )
        if created:
            print(f"  ✓ Photographer: {user.username}")
        else:
            print(f"  - Skip (exists): {user.username}")
    except User.DoesNotExist:
        print(f"  ! User tidak ditemukan: {data['username']}")

print(f"  Total photographers: {Photographer.objects.count()}")


# ─── 4. IMPORT BOOKING ────────────────────────────────────────────────────────
print("\n[4/5] Importing bookings...")

photographers = list(Photographer.objects.all())

with open(filepath + 'booking-data.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    obj_create = []

    for num, row in enumerate(reader):
        if not Booking.objects.filter(pk=num + 1).exists():
            try:
                client  = User.objects.get(pk=int(row['client_id']))
                package = Package.objects.get(pk=int(row['package_id']))
                # Assign fotografer secara round-robin
                photographer = photographers[num % len(photographers)] if photographers else None

                obj_create.append(Booking(
                    id=num + 1,
                    client=client,
                    package=package,
                    photographer=photographer,
                    event_type=row['event_type'],
                    event_date=row['event_date'],
                    location=row['location'],
                    notes=row['notes'],
                    status=row['status'],
                    total_price=int(row['total_price']),
                ))
            except (User.DoesNotExist, Package.DoesNotExist) as e:
                print(f"  ! Error row {num+1}: {e}")

    # ✅ bulk_create — insert semua sekaligus (1 query, bukan N query)
    if obj_create:
        Booking.objects.bulk_create(obj_create)
        print(f"  ✓ {len(obj_create)} bookings imported (bulk_create)")
    else:
        print("  - Semua booking sudah ada")

print(f"  Total bookings: {Booking.objects.count()}")


# ─── 5. IMPORT REVIEW ─────────────────────────────────────────────────────────
print("\n[5/5] Importing reviews...")

REVIEWS = [
    {'booking_id': 1, 'rating': 5, 'comment': 'Veloura Visual luar biasa! Foto pernikahan kami sangat indah dan penuh emosi.'},
    {'booking_id': 2, 'rating': 5, 'comment': 'Fotografernya profesional dan ramah. Hasil foto memuaskan!'},
    {'booking_id': 4, 'rating': 5, 'comment': 'Sangat puas dengan hasilnya. Setiap momen wisuda terabadikan dengan sempurna.'},
    {'booking_id': 7, 'rating': 4, 'comment': 'Foto OOTD hasilnya bagus, hanya sedikit terlambat datang.'},
    {'booking_id': 9, 'rating': 5, 'comment': 'Pre-wedding kami jadi sangat berkesan berkat Veloura Visual!'},
    {'booking_id': 12, 'rating': 4, 'comment': 'Foto ulang tahun anak kami sangat lucu dan natural.'},
    {'booking_id': 13, 'rating': 5, 'comment': 'Foto produk UMKM kami jadi terlihat profesional. Terima kasih!'},
]

review_create = []
for data in REVIEWS:
    try:
        booking = Booking.objects.get(pk=data['booking_id'])
        if not Review.objects.filter(booking=booking).exists():
            review_create.append(Review(
                booking=booking,
                rating=data['rating'],
                comment=data['comment'],
                is_public=True,
            ))
    except Booking.DoesNotExist:
        print(f"  ! Booking {data['booking_id']} tidak ditemukan")

# ✅ bulk_create untuk review
if review_create:
    Review.objects.bulk_create(review_create)
    print(f"  ✓ {len(review_create)} reviews imported (bulk_create)")
else:
    print("  - Semua review sudah ada")

print(f"  Total reviews: {Review.objects.count()}")

print("\n" + "=" * 50)
print("IMPORT SELESAI ✓")
print("=" * 50)
