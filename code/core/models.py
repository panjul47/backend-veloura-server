"""
Models untuk Veloura Visual — Jasa Fotografi

Relational Mapping (ORM) mencakup:
- ForeignKey (One-to-Many): Booking -> User, BookingContent -> Booking, dll
- Self-referential ForeignKey: BookingContent -> BookingContent (parent/child konten)
- Choices field: PACKAGE_OPTIONS, ROLE_OPTIONS, STATUS_OPTIONS
- Auto timestamps: created_at, updated_at
"""

from django.db import models
from django.contrib.auth.models import User


# ─── PAKET FOTO ───────────────────────────────────────────────────────────────

PACKAGE_TYPE = [
    ('harian', 'Harian'),
    ('event',  'Event'),
]

PACKAGE_TIER = [
    ('basic',    'Basic'),
    ('standard', 'Standard'),
    ('premium',  'Premium'),
]


class Package(models.Model):
    """
    Paket layanan fotografi yang ditawarkan Veloura Visual.
    Relasi: One-to-Many ke Booking (satu paket bisa dipesan banyak kali)
    """
    name         = models.CharField("nama paket", max_length=100)
    description  = models.TextField("deskripsi", default='-')
    price        = models.IntegerField("harga", default=300000)
    duration     = models.CharField("durasi", max_length=50, default='2 jam')
    package_type = models.CharField("tipe", max_length=10, choices=PACKAGE_TYPE, default='harian')
    package_tier = models.CharField("tier", max_length=10, choices=PACKAGE_TIER, default='basic')
    is_featured  = models.BooleanField("unggulan", default=False)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Paket"
        verbose_name_plural = "Paket"
        ordering            = ['package_type', 'price']

    def __str__(self):
        return f"{self.name} ({self.get_package_type_display()}) - Rp{self.price:,}"


class PackageFeature(models.Model):
    """
    Fitur-fitur yang termasuk dalam sebuah paket.
    Relasi: Many-to-One ke Package (banyak fitur untuk satu paket)
    """
    package     = models.ForeignKey(Package, verbose_name="paket",
                                    on_delete=models.CASCADE,
                                    related_name='features')
    description = models.CharField("fitur", max_length=200)
    order       = models.PositiveSmallIntegerField("urutan", default=0)

    class Meta:
        verbose_name        = "Fitur Paket"
        verbose_name_plural = "Fitur Paket"
        ordering            = ['order']

    def __str__(self):
        return f"{self.package.name} — {self.description}"


# ─── BOOKING ──────────────────────────────────────────────────────────────────

STATUS_OPTIONS = [
    ('pending',    'Menunggu Konfirmasi'),
    ('confirmed',  'Dikonfirmasi'),
    ('in_progress','Sedang Berlangsung'),
    ('done',       'Selesai'),
    ('cancelled',  'Dibatalkan'),
]

EVENT_TYPE = [
    ('wedding',    'Pernikahan'),
    ('graduation', 'Wisuda'),
    ('birthday',   'Ulang Tahun'),
    ('corporate',  'Korporat'),
    ('daily',      'Foto Harian'),
    ('other',      'Lainnya'),
]


class Booking(models.Model):
    """
    Pemesanan jasa fotografi oleh klien.
    Relasi:
    - ForeignKey ke User (klien yang memesan)
    - ForeignKey ke Package (paket yang dipilih)
    - ForeignKey ke Photographer (fotografer yang ditugaskan, nullable)
    """
    client       = models.ForeignKey(User, verbose_name="klien",
                                     on_delete=models.RESTRICT,
                                     related_name='bookings')
    package      = models.ForeignKey(Package, verbose_name="paket",
                                     on_delete=models.RESTRICT,
                                     related_name='bookings')
    photographer = models.ForeignKey('Photographer', verbose_name="fotografer",
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name='bookings')
    event_type   = models.CharField("jenis acara", max_length=20,
                                    choices=EVENT_TYPE, default='other')
    event_date   = models.DateField("tanggal acara")
    location     = models.CharField("lokasi", max_length=200)
    notes        = models.TextField("catatan tambahan", blank=True, default='')
    status       = models.CharField("status", max_length=15,
                                    choices=STATUS_OPTIONS, default='pending')
    total_price  = models.IntegerField("total harga", default=0)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Pemesanan"
        verbose_name_plural = "Pemesanan"
        ordering            = ['-event_date']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.client.username} — {self.package.name} ({self.event_date})"

    def save(self, *args, **kwargs):
        # Auto-set total_price dari package saat pertama kali dibuat
        if not self.total_price:
            self.total_price = self.package.price
        super().save(*args, **kwargs)


# ─── FOTOGRAFER ───────────────────────────────────────────────────────────────

SPECIALIZATION = [
    ('wedding',    'Wedding'),
    ('portrait',   'Portrait'),
    ('event',      'Event'),
    ('product',    'Product'),
    ('landscape',  'Landscape'),
]


class Photographer(models.Model):
    """
    Profil fotografer Veloura Visual.
    Relasi: One-to-One ke User (setiap fotografer punya akun user)
    """
    user           = models.OneToOneField(User, verbose_name="akun",
                                          on_delete=models.CASCADE,
                                          related_name='photographer_profile')
    bio            = models.TextField("bio", blank=True, default='')
    specialization = models.CharField("spesialisasi", max_length=20,
                                      choices=SPECIALIZATION, default='event')
    portfolio_url  = models.URLField("portfolio", blank=True, null=True)
    is_available   = models.BooleanField("tersedia", default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Fotografer"
        verbose_name_plural = "Fotografer"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_specialization_display()})"


# ─── GALERI / HASIL FOTO ──────────────────────────────────────────────────────

class Gallery(models.Model):
    """
    Galeri hasil foto dari sebuah booking.
    Relasi: Many-to-One ke Booking
    Self-referential ForeignKey untuk album bersarang (parent/child)
    """
    booking     = models.ForeignKey(Booking, verbose_name="pemesanan",
                                    on_delete=models.CASCADE,
                                    related_name='gallery_items')
    parent      = models.ForeignKey("self", verbose_name="album induk",
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='children')
    title       = models.CharField("judul", max_length=200)
    description = models.TextField("deskripsi", blank=True, default='')
    image_url   = models.URLField("URL foto", blank=True, null=True)
    file        = models.FileField("file foto", null=True, blank=True,
                                   upload_to='gallery/')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Galeri"
        verbose_name_plural = "Galeri"
        ordering            = ['-created_at']

    def __str__(self):
        return f"[{self.booking}] {self.title}"


# ─── REVIEW / TESTIMONI ───────────────────────────────────────────────────────

RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]  # 1–5 bintang


class Review(models.Model):
    """
    Review/testimoni dari klien setelah booking selesai.
    Relasi: One-to-One ke Booking (satu booking satu review)
    """
    booking    = models.OneToOneField(Booking, verbose_name="pemesanan",
                                      on_delete=models.CASCADE,
                                      related_name='review')
    rating     = models.PositiveSmallIntegerField("rating", choices=RATING_CHOICES, default=5)
    comment    = models.TextField("komentar")
    photo      = models.ImageField("foto klien", upload_to='reviews/', null=True, blank=True)
    is_public  = models.BooleanField("tampilkan di publik", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Review"
        verbose_name_plural = "Review"
        ordering            = ['-created_at']

    def __str__(self):
        return f"⭐{self.rating} — {self.booking.client.username} ({self.booking.package.name})"
