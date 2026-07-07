"""
Integration Test — API Endpoints Veloura Visual
Menguji endpoint REST API (Django Ninja) dari sisi HTTP request/response.

Jalankan:
    docker exec simple_lms python manage.py test core.tests.test_views --verbosity=2
"""

import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from core.models import Package, PackageFeature, Booking, Review


class PackageAPITest(TestCase):
    """Integration test untuk endpoint /api/v1/packages/"""

    def setUp(self):
        self.client = Client()
        self.pkg1 = Package.objects.create(
            name='Harian Basic',
            description='Paket harian basic',
            price=300000,
            duration='2 jam',
            package_type='harian',
            package_tier='basic',
            is_featured=False,
        )
        self.pkg2 = Package.objects.create(
            name='Wedding Premium',
            description='Paket wedding premium',
            price=5000000,
            duration='8 jam',
            package_type='event',
            package_tier='premium',
            is_featured=True,
        )
        PackageFeature.objects.create(
            package=self.pkg1, description='2 jam sesi foto', order=1
        )

    def test_get_packages_returns_200(self):
        """GET /api/v1/packages/ harus return status 200"""
        response = self.client.get('/api/v1/packages/')
        self.assertEqual(response.status_code, 200)

    def test_get_packages_returns_list(self):
        """GET /api/v1/packages/ harus return list paket"""
        response = self.client.get('/api/v1/packages/')
        data = json.loads(response.content)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)

    def test_get_packages_filter_by_type(self):
        """Filter ?package_type=harian harus hanya return paket harian"""
        response = self.client.get('/api/v1/packages/?package_type=harian')
        data = json.loads(response.content)
        for pkg in data:
            self.assertIn('Harian', pkg['package_type'])

    def test_get_packages_filter_by_price(self):
        """Filter ?price_lte=500000 hanya return paket di bawah 500rb"""
        response = self.client.get('/api/v1/packages/?price_lte=500000')
        data = json.loads(response.content)
        for pkg in data:
            self.assertLessEqual(pkg['price'], 500000)

    def test_get_packages_filter_search(self):
        """Filter ?search=wedding harus menemukan paket wedding"""
        response = self.client.get('/api/v1/packages/?search=wedding')
        data = json.loads(response.content)
        self.assertTrue(
            any('wedding' in p['name'].lower() or 'wedding' in p['description'].lower()
                for p in data)
        )

    def test_get_package_detail_returns_200(self):
        """GET /api/v1/packages/{id}/ harus return 200 untuk ID valid"""
        response = self.client.get(f'/api/v1/packages/{self.pkg1.id}/')
        self.assertEqual(response.status_code, 200)

    def test_get_package_detail_contains_features(self):
        """Detail paket harus menyertakan list features"""
        response = self.client.get(f'/api/v1/packages/{self.pkg1.id}/')
        data = json.loads(response.content)
        self.assertIn('features', data)
        self.assertIsInstance(data['features'], list)

    def test_get_package_detail_not_found(self):
        """GET /api/v1/packages/9999/ harus return 404"""
        response = self.client.get('/api/v1/packages/9999/')
        self.assertEqual(response.status_code, 404)

    def test_get_package_stats_returns_200(self):
        """GET /api/v1/package-stats/ harus return 200"""
        response = self.client.get('/api/v1/package-stats/')
        self.assertEqual(response.status_code, 200)

    def test_get_package_stats_contains_required_keys(self):
        """Statistik paket harus mengandung total_packages dan price_stats"""
        response = self.client.get('/api/v1/package-stats/')
        data = json.loads(response.content)
        self.assertIn('total_packages', data)
        self.assertIn('price_stats', data)
        self.assertEqual(data['total_packages'], 2)


class BookingAPITest(TestCase):
    """Integration test untuk endpoint /api/v1/bookings/"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@veloura.com',
        )
        self.package = Package.objects.create(
            name='Event Basic',
            price=1000000,
            package_type='event',
            package_tier='basic',
        )
        self.booking = Booking.objects.create(
            client=self.user,
            package=self.package,
            event_type='wedding',
            event_date='2026-09-01',
            location='Semarang Convention Center',
            status='confirmed',
        )

    def test_get_bookings_returns_200(self):
        """GET /api/v1/bookings/ harus return 200"""
        response = self.client.get('/api/v1/bookings/')
        self.assertEqual(response.status_code, 200)

    def test_get_bookings_returns_list(self):
        """GET /api/v1/bookings/ harus return list"""
        response = self.client.get('/api/v1/bookings/')
        data = json.loads(response.content)
        self.assertIsInstance(data, list)

    def test_get_bookings_filter_by_status(self):
        """Filter ?status=confirmed hanya return booking confirmed"""
        response = self.client.get('/api/v1/bookings/?status=confirmed')
        data = json.loads(response.content)
        for booking in data:
            self.assertEqual(booking['status'], 'Dikonfirmasi')

    def test_get_bookings_filter_by_event_type(self):
        """Filter ?event_type=wedding hanya return booking wedding"""
        response = self.client.get('/api/v1/bookings/?event_type=wedding')
        data = json.loads(response.content)
        for booking in data:
            self.assertEqual(booking['event_type'], 'Pernikahan')

    def test_get_booking_detail_returns_200(self):
        """GET /api/v1/bookings/{id}/ harus return 200"""
        response = self.client.get(f'/api/v1/bookings/{self.booking.id}/')
        self.assertEqual(response.status_code, 200)

    def test_get_booking_detail_contains_client(self):
        """Detail booking harus menyertakan data client"""
        response = self.client.get(f'/api/v1/bookings/{self.booking.id}/')
        data = json.loads(response.content)
        self.assertIn('client', data)
        self.assertEqual(data['client']['username'], 'testuser')

    def test_get_booking_detail_not_found(self):
        """GET /api/v1/bookings/9999/ harus return 404"""
        response = self.client.get('/api/v1/bookings/9999/')
        self.assertEqual(response.status_code, 404)

    def test_get_booking_stats_returns_200(self):
        """GET /api/v1/booking-stats/ harus return 200"""
        response = self.client.get('/api/v1/booking-stats/')
        self.assertEqual(response.status_code, 200)

    def test_get_booking_stats_contains_required_keys(self):
        """Statistik booking harus ada total_bookings dan revenue"""
        response = self.client.get('/api/v1/booking-stats/')
        data = json.loads(response.content)
        self.assertIn('total_bookings', data)
        self.assertIn('revenue', data)
        self.assertIn('status_breakdown', data)


class ReviewAPITest(TestCase):
    """Integration test untuk endpoint /api/v1/reviews/"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='reviewer', password='pass123',
            first_name='Andi', last_name='Wijaya',
        )
        self.package = Package.objects.create(
            name='Harian Standard',
            price=600000,
            package_type='harian',
            package_tier='standard',
        )
        self.booking = Booking.objects.create(
            client=self.user,
            package=self.package,
            event_type='daily',
            event_date='2026-06-01',
            location='Jakarta',
            status='done',
        )
        self.review = Review.objects.create(
            booking=self.booking,
            rating=5,
            comment='Hasil foto sangat memuaskan!',
            is_public=True,
        )

    def test_get_reviews_returns_200(self):
        """GET /api/v1/reviews/ harus return 200"""
        response = self.client.get('/api/v1/reviews/')
        self.assertEqual(response.status_code, 200)

    def test_get_reviews_only_public(self):
        """GET /api/v1/reviews/ hanya menampilkan review yang is_public=True"""
        # Buat review private
        user2 = User.objects.create_user(username='user2', password='pass')
        pkg2  = Package.objects.create(name='Pkg2', price=100000, package_type='harian', package_tier='basic')
        booking2 = Booking.objects.create(
            client=user2, package=pkg2,
            event_type='other', event_date='2026-05-01',
            location='Solo', status='done',
        )
        Review.objects.create(
            booking=booking2, rating=2,
            comment='Review private ini tidak boleh muncul.',
            is_public=False,
        )
        response = self.client.get('/api/v1/reviews/')
        data = json.loads(response.content)
        # Hanya 1 review public yang dibuat di setUp
        self.assertEqual(len(data), 1)

    def test_get_reviews_filter_by_rating(self):
        """Filter ?rating_gte=5 hanya return review dengan rating 5"""
        response = self.client.get('/api/v1/reviews/?rating_gte=5')
        data = json.loads(response.content)
        for review in data:
            self.assertGreaterEqual(review['rating'], 5)

    def test_get_reviews_contains_required_fields(self):
        """Setiap review harus punya field: rating, comment, client_username"""
        response = self.client.get('/api/v1/reviews/')
        data = json.loads(response.content)
        self.assertTrue(len(data) > 0)
        review = data[0]
        self.assertIn('rating', review)
        self.assertIn('comment', review)
        self.assertIn('client_username', review)
        self.assertIn('package_name', review)

    def test_get_review_stats_returns_200(self):
        """GET /api/v1/review-stats/ harus return 200"""
        response = self.client.get('/api/v1/review-stats/')
        self.assertEqual(response.status_code, 200)

    def test_get_review_stats_overall_avg(self):
        """overall_avg harus sesuai dengan rating yang ada"""
        response = self.client.get('/api/v1/review-stats/')
        data = json.loads(response.content)
        self.assertEqual(data['overall_avg'], 5.0)
        self.assertEqual(data['total_reviews'], 1)


class RegisterAPITest(TestCase):
    """Integration test untuk endpoint POST /api/v1/register/"""

    def setUp(self):
        self.client = Client()
        # Override cache ke dummy agar throttle tidak aktif saat testing
        from django.test.utils import override_settings
        self._cache_override = override_settings(
            CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
        )
        self._cache_override.__enter__()

    def tearDown(self):
        self._cache_override.__exit__(None, None, None)

    def test_register_success(self):
        """Register dengan data valid harus return 200 dan user baru"""
        payload = {
            'username': 'newuser01',
            'password': 'pass1234',
            'email':    'newuser@veloura.com',
            'first_name': 'Baru',
            'last_name':  'User',
        }
        response = self.client.post(
            '/api/v1/register/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['username'], 'newuser01')
        self.assertIn('id', data)

    def test_register_username_too_short(self):
        """Username kurang dari 5 karakter harus return error validasi"""
        payload = {
            'username': 'usr',
            'password': 'pass1234',
            'email':    'short@test.com',
            'first_name': 'A',
            'last_name':  'B',
        }
        response = self.client.post(
            '/api/v1/register/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 422)

    def test_register_password_no_number(self):
        """Password tanpa angka harus return error validasi"""
        payload = {
            'username': 'validuser',
            'password': 'passwordsaja',
            'email':    'valid@test.com',
            'first_name': 'Valid',
            'last_name':  'User',
        }
        response = self.client.post(
            '/api/v1/register/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 422)

    def test_register_duplicate_username(self):
        """Username yang sudah ada harus return 400"""
        User.objects.create_user(
            username='existinguser', password='pass123'
        )
        payload = {
            'username': 'existinguser',
            'password': 'newpass123',
            'email':    'new@test.com',
            'first_name': 'New',
            'last_name':  'User',
        }
        response = self.client.post(
            '/api/v1/register/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_register_invalid_email(self):
        """Email tidak valid harus return error validasi"""
        payload = {
            'username': 'validuser2',
            'password': 'pass1234',
            'email':    'bukan-email',
            'first_name': 'Test',
            'last_name':  'User',
        }
        response = self.client.post(
            '/api/v1/register/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 422)
