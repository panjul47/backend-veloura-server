"""
Unit Test — Models Veloura Visual
Menguji behaviour model secara terisolasi.

Jalankan:
    docker exec simple_lms python manage.py test core.tests.test_models --verbosity=2
"""

from django.test import TestCase
from django.contrib.auth.models import User
from core.models import Package, PackageFeature, Booking, Photographer, Review


class PackageModelTest(TestCase):
    """Unit test untuk model Package"""

    def setUp(self):
        """Siapkan data test yang dipakai di semua test method"""
        self.package = Package.objects.create(
            name='Wedding Premium',
            description='Paket fotografi pernikahan premium',
            price=5000000,
            duration='8 jam',
            package_type='event',
            package_tier='premium',
            is_featured=True,
        )

    def test_str_method(self):
        """__str__ harus menampilkan nama, tipe, dan harga"""
        self.assertIn('Wedding Premium', str(self.package))
        self.assertIn('Event', str(self.package))

    def test_package_type_display(self):
        """get_package_type_display harus return label yang benar"""
        self.assertEqual(self.package.get_package_type_display(), 'Event')

    def test_package_tier_display(self):
        """get_package_tier_display harus return label yang benar"""
        self.assertEqual(self.package.get_package_tier_display(), 'Premium')

    def test_is_featured_default_false(self):
        """Paket baru tanpa is_featured harus default False"""
        pkg = Package.objects.create(
            name='Basic Harian',
            price=300000,
            package_type='harian',
            package_tier='basic',
        )
        self.assertFalse(pkg.is_featured)

    def test_package_has_features(self):
        """Package bisa punya banyak PackageFeature"""
        PackageFeature.objects.create(
            package=self.package,
            description='Free konsultasi',
            order=1,
        )
        PackageFeature.objects.create(
            package=self.package,
            description='Album foto',
            order=2,
        )
        self.assertEqual(self.package.features.count(), 2)

    def test_package_feature_str(self):
        """__str__ PackageFeature harus menyebut nama paket"""
        feature = PackageFeature.objects.create(
            package=self.package,
            description='Free drone shot',
            order=1,
        )
        self.assertIn('Wedding Premium', str(feature))
        self.assertIn('Free drone shot', str(feature))


class BookingModelTest(TestCase):
    """Unit test untuk model Booking"""

    def setUp(self):
        self.client_user = User.objects.create_user(
            username='testklien',
            password='testpass123',
            email='klien@test.com',
        )
        self.package = Package.objects.create(
            name='Harian Basic',
            price=300000,
            package_type='harian',
            package_tier='basic',
        )

    def test_booking_auto_set_total_price(self):
        """total_price harus otomatis diisi dari package.price saat booking dibuat"""
        booking = Booking.objects.create(
            client=self.client_user,
            package=self.package,
            event_type='daily',
            event_date='2026-08-01',
            location='Jakarta Selatan',
        )
        self.assertEqual(booking.total_price, self.package.price)

    def test_booking_default_status_pending(self):
        """Status booking baru harus 'pending'"""
        booking = Booking.objects.create(
            client=self.client_user,
            package=self.package,
            event_type='daily',
            event_date='2026-08-01',
            location='Jakarta Selatan',
        )
        self.assertEqual(booking.status, 'pending')

    def test_booking_str_contains_username_and_package(self):
        """__str__ booking harus menyebut username dan nama paket"""
        booking = Booking.objects.create(
            client=self.client_user,
            package=self.package,
            event_type='daily',
            event_date='2026-08-01',
            location='Jakarta Selatan',
        )
        self.assertIn('testklien', str(booking))
        self.assertIn('Harian Basic', str(booking))

    def test_booking_total_price_not_overwritten_if_already_set(self):
        """total_price yang sudah diisi manual tidak boleh ditimpa"""
        booking = Booking.objects.create(
            client=self.client_user,
            package=self.package,
            event_type='daily',
            event_date='2026-08-01',
            location='Jakarta',
            total_price=999999,
        )
        self.assertEqual(booking.total_price, 999999)


class PhotographerModelTest(TestCase):
    """Unit test untuk model Photographer"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='fotografer01',
            first_name='Budi',
            last_name='Santoso',
            password='pass123',
        )
        self.photographer = Photographer.objects.create(
            user=self.user,
            specialization='wedding',
            is_available=True,
        )

    def test_photographer_str_contains_name(self):
        """__str__ fotografer harus menyebut nama lengkap atau username"""
        self.assertIn('Budi', str(self.photographer))

    def test_photographer_specialization_display(self):
        """get_specialization_display harus return label yang benar"""
        self.assertEqual(self.photographer.get_specialization_display(), 'Wedding')

    def test_photographer_is_available_default_true(self):
        """Fotografer baru harus default tersedia"""
        self.assertTrue(self.photographer.is_available)

    def test_photographer_one_to_one_user(self):
        """Satu user hanya boleh punya satu profil fotografer"""
        from django.db import IntegrityError
        with self.assertRaises(Exception):
            Photographer.objects.create(
                user=self.user,
                specialization='portrait',
            )


class ReviewModelTest(TestCase):
    """Unit test untuk model Review"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='reviewer01', password='pass123'
        )
        self.package = Package.objects.create(
            name='Event Standard',
            price=1500000,
            package_type='event',
            package_tier='standard',
        )
        self.booking = Booking.objects.create(
            client=self.user,
            package=self.package,
            event_type='wedding',
            event_date='2026-07-01',
            location='Semarang',
            status='done',
        )

    def test_review_str_contains_rating_and_username(self):
        """__str__ review harus menyebut rating dan username klien"""
        review = Review.objects.create(
            booking=self.booking,
            rating=5,
            comment='Sangat puas dengan hasilnya!',
        )
        self.assertIn('5', str(review))
        self.assertIn('reviewer01', str(review))

    def test_review_default_is_public_true(self):
        """Review baru harus default tampil di publik"""
        review = Review.objects.create(
            booking=self.booking,
            rating=4,
            comment='Hasil foto bagus sekali.',
        )
        self.assertTrue(review.is_public)

    def test_one_booking_one_review(self):
        """Satu booking hanya boleh punya satu review"""
        Review.objects.create(
            booking=self.booking,
            rating=5,
            comment='Review pertama.',
        )
        from django.db import IntegrityError
        with self.assertRaises(Exception):
            Review.objects.create(
                booking=self.booking,
                rating=3,
                comment='Review kedua — tidak boleh.',
            )
