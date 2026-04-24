# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies into a separate layer for better cache reuse.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder.
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin/uvicorn    /usr/local/bin/uvicorn

# Copy application source.
COPY main.py .
COPY routes/  routes/
COPY models/  models/
COPY services/ services/

# Run as a non-root user.
RUN useradd --no-create-home --shell /bin/false appuser \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Single worker keeps the in-memory rate limiter consistent.
# Replace with a Redis-backed limiter before running multiple replicas.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
