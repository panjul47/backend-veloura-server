#!/bin/sh
# entrypoint.sh — jalankan migrate & collectstatic sebelum gunicorn start

set -e

echo ">>> Running migrations..."
python /code/manage.py migrate --no-input

echo ">>> Collecting static files..."
python /code/manage.py collectstatic --no-input

echo ">>> Starting Gunicorn..."
exec gunicorn simplelms.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
