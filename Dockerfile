# Dockerfile — Veloura Visual Backend
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /code

# Install dependencies
COPY code/requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY code/ /code/

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Buat folder yang diperlukan
RUN mkdir -p /code/logs /code/staticfiles /code/media

# Buat user non-root
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set ownership SETELAH copy dan mkdir
RUN chown -R appuser:appgroup /code

# Switch ke non-root user
USER appuser

CMD ["/entrypoint.sh"]
