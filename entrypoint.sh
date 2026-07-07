#!/bin/sh
# entrypoint.sh — jalankan migrate & collectstatic sebelum gunicorn start

set -e

echo ">>> Running migrations..."
python manage.py migrate --no-input

echo ">>> Collecting static files..."
python manage.py collectstatic --no-input

echo ">>> Starting Gunicorn..."
exec gunicorn simplelms.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
