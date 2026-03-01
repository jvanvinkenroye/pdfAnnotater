# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM python:3.12.9-slim-bookworm AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /build

# Install dependencies (cached separately from source)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Install gunicorn for production WSGI
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install "gunicorn>=23.0.0"

# Copy and install the project itself
COPY src/ ./src/
COPY wsgi.py ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12.9-slim-bookworm

# Non-root user (principle of least privilege)
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home --shell /sbin/nologin appuser

# Data directory (SQLite DB, uploads, exports, logs)
RUN mkdir -p /data && chown appuser:appuser /data

WORKDIR /app

# Copy virtual environment and application from builder
COPY --from=builder --chown=appuser:appuser /build/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /build/src    /app/src
COPY --from=builder --chown=appuser:appuser /build/wsgi.py /app/wsgi.py

USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    APP_ENV=production \
    # On Linux, XDG_DATA_HOME controls where ProductionConfig stores data.
    # get_data_dir() returns $XDG_DATA_HOME/PDF-Annotator/
    XDG_DATA_HOME=/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/auth/login')" || exit 1

# exec replaces the shell so gunicorn receives SIGTERM directly (graceful shutdown).
# Shell form is needed only for ${GUNICORN_WORKERS:-2} expansion.
CMD ["sh", "-c", "exec gunicorn --workers ${GUNICORN_WORKERS:-2} --bind 0.0.0.0:8000 --timeout 120 --access-logfile - --error-logfile - wsgi:app"]
