"""
Django settings untuk Veloura Visual.
Production-ready: semua secret dari env vars, tidak ada data bocor.
"""

from pathlib import Path
from django.urls import reverse_lazy
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── SECURITY ─────────────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set!")

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

_allowed = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _allowed.split(',') if h.strip()]

# Railway healthcheck menggunakan 'healthcheck.railway.app' sebagai Host header
# Tambahkan otomatis agar tidak perlu update manual setiap deploy
ALLOWED_HOSTS += ['localhost', '127.0.0.1', '.railway.app']

# ─── APPLICATIONS ─────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'unfold.contrib.inlines',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'corsheaders',
    'ninja_simple_jwt',
]

if DEBUG:
    INSTALLED_APPS.append('silk')

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serve static files di production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG:
    MIDDLEWARE.insert(0, 'silk.middleware.SilkyMiddleware')

# ─── SECURITY HEADERS ─────────────────────────────────────────────────────────

# Aktif di semua environment
X_FRAME_OPTIONS              = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF  = True
SECURE_BROWSER_XSS_FILTER    = True

if not DEBUG:
    # HTTPS enforcement — aktifkan hanya jika sudah ada SSL/reverse proxy
    # Set SECURE_SSL_REDIRECT=True di production dengan HTTPS
    SECURE_SSL_REDIRECT               = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
    SECURE_HSTS_SECONDS               = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS    = True
    SECURE_HSTS_PRELOAD               = True
    SECURE_PROXY_SSL_HEADER           = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Cookie security
    SESSION_COOKIE_SECURE             = True
    SESSION_COOKIE_HTTPONLY           = True
    SESSION_COOKIE_SAMESITE           = 'Lax'
    CSRF_COOKIE_SECURE                = True
    CSRF_COOKIE_HTTPONLY              = True

# ─── CORS ─────────────────────────────────────────────────────────────────────

CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS', 'http://localhost:5173'
).split(',')

# Tidak izinkan semua origin
CORS_ALLOW_ALL_ORIGINS = False

# ─── URLS ─────────────────────────────────────────────────────────────────────

ROOT_URLCONF = 'simplelms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'simplelms.wsgi.application'

# ─── DATABASE ─────────────────────────────────────────────────────────────────
# Mendukung DATABASE_URL (Render/Supabase) atau variabel terpisah (Railway)

import dj_database_url

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Render / Supabase — pakai connection string
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=60,
            conn_health_checks=True,
        )
    }
else:
    # Railway / lokal — pakai variabel terpisah
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql_psycopg2',
            'NAME':     os.environ.get('POSTGRES_DB')   or os.environ.get('PGDATABASE', 'veloura_db'),
            'USER':     os.environ.get('POSTGRES_USER') or os.environ.get('PGUSER', 'veloura_user'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD') or os.environ.get('PGPASSWORD', ''),
            'HOST':     os.environ.get('POSTGRES_HOST') or os.environ.get('PGHOST', 'postgres'),
            'PORT':     os.environ.get('POSTGRES_PORT') or os.environ.get('PGPORT', '5432'),
            'OPTIONS':  {'connect_timeout': 10},
            'CONN_MAX_AGE': 60,
        }
    }

# ─── CACHE (untuk throttling Django Ninja) ────────────────────────────────────

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'veloura-throttle-cache',
    }
}

# ─── PASSWORD VALIDATION ──────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── LOGGING ──────────────────────────────────────────────────────────────────
# Error log ke file, TIDAK menampilkan traceback ke client

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ─── INTERNATIONALIZATION ─────────────────────────────────────────────────────

LANGUAGE_CODE = 'id'
TIME_ZONE     = 'Asia/Jakarta'
USE_I18N      = True
USE_TZ        = True

# ─── STATIC & MEDIA ───────────────────────────────────────────────────────────

STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL   = '/media/'
MEDIA_ROOT  = BASE_DIR / 'media'

# WhiteNoise — serve static files langsung dari Gunicorn
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── FILE UPLOAD SECURITY ─────────────────────────────────────────────────────

# Maksimal ukuran file upload: 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ─── UNFOLD ADMIN ─────────────────────────────────────────────────────────────

UNFOLD = {
    "SITE_TITLE":    "Veloura Visual",
    "SITE_HEADER":   "Veloura Visual",
    "SITE_SUBHEADER": "Photography Management",
    "SITE_URL":      "/",
    "SITE_ICON":     None,
    "SITE_SYMBOL":   "camera_alt",
    "SHOW_HISTORY":  True,
    "SHOW_VIEW_ON_SITE": True,
    "THEME": None,
    "COLORS": {
        "primary": {
            "50":  "250 245 255", "100": "243 232 255", "200": "233 213 255",
            "300": "216 180 254", "400": "192 132 252", "500": "168 85 247",
            "600": "147 51 234",  "700": "126 34 206",  "800": "107 33 168",
            "900": "88 28 135",   "950": "59 7 100",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Navigasi",
                "separator": False,
                "items": [{"title": "Dashboard", "icon": "dashboard",
                           "link": lambda request: reverse_lazy("admin:index")}],
            },
            {
                "title": "Manajemen Booking",
                "separator": True,
                "items": [
                    {"title": "Booking",    "icon": "event_note",
                     "link": lambda request: reverse_lazy("admin:core_booking_changelist")},
                    {"title": "Paket",      "icon": "inventory_2",
                     "link": lambda request: reverse_lazy("admin:core_package_changelist")},
                    {"title": "Fotografer", "icon": "photo_camera",
                     "link": lambda request: reverse_lazy("admin:core_photographer_changelist")},
                ],
            },
            {
                "title": "Konten & Review",
                "separator": True,
                "items": [
                    {"title": "Galeri",  "icon": "photo_library",
                     "link": lambda request: reverse_lazy("admin:core_gallery_changelist")},
                    {"title": "Review",  "icon": "star",
                     "link": lambda request: reverse_lazy("admin:core_review_changelist")},
                ],
            },
            {
                "title": "Pengguna",
                "separator": True,
                "items": [
                    {"title": "Users",  "icon": "person",
                     "link": lambda request: reverse_lazy("admin:auth_user_changelist")},
                    {"title": "Groups", "icon": "group",
                     "link": lambda request: reverse_lazy("admin:auth_group_changelist")},
                ],
            },
        ],
    },
}
