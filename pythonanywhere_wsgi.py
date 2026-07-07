"""
WSGI config untuk PythonAnywhere deployment.

Letakkan path ini di PythonAnywhere Web tab → WSGI configuration file.
Ganti 'yourusername' dengan username PythonAnywhere kamu.
"""

import os
import sys

# Path ke folder code Django
path = '/home/yourusername/backend-veloura-pss/code'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'simplelms.settings'
os.environ['SECRET_KEY'] = '@-wq8ym0e8b3_)k#wy$a5y=k_4w)aozrzha+3i93n^b=#=o8^r'
os.environ['DEBUG'] = 'False'
os.environ['ALLOWED_HOSTS'] = 'yourusername.pythonanywhere.com'
os.environ['DATABASE_URL'] = 'postgresql://...'  # isi dari Supabase
os.environ['CORS_ALLOWED_ORIGINS'] = 'https://your-app.vercel.app'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
