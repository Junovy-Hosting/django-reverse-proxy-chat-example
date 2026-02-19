# -- Builder stage: install Python dependencies --
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# -- Runtime stage --
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user
RUN addgroup --system app && adduser --system --ingroup app app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY src/ .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create staticfiles directory and set ownership
RUN mkdir -p /app/staticfiles && chown -R app:app /app

USER app

ENTRYPOINT ["/entrypoint.sh"]

# Daphne serves both HTTP and WebSocket via ASGI
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "faenet.asgi:application"]
