# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for headcleaner.
# Build:   docker build -t headcleaner:dev .
# Run:     docker run --rm -v /path/to/inbox:/inbox -v /path/to/out:/out headcleaner:dev convert /inbox --output /out
#
# Image is ~150 MB compressed (Python 3.12 + deps).
# OfficeCLI is NOT bundled; if you need Office-format conversion, mount
# the officecli binary into the container (see Dockerfile comment block
# below).

ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.4

# --- Builder stage -----------------------------------------------------------
FROM ghcr.io/astral-sh/uv:${UV_VERSION}-python${PYTHON_VERSION}-bookworm-slim AS builder

WORKDIR /build
# Build the environment at its final runtime path so console-script shebangs
# remain valid after the multi-stage copy.
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Install build deps for any wheels that need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first (cache layer)
COPY pyproject.toml uv.lock README.md ./

# Install only portable runtime extras. PST extraction is provided by the
# distro's readpst binary in the runtime stage; libpff-python is deliberately
# excluded because it has no Linux wheel and would require a source build.
RUN uv sync --frozen --no-install-project --extra ocr --no-dev

# Copy source + build wheel
COPY src ./src
RUN uv build --wheel --out-dir /build/dist

# Install the built wheel into the same venv
RUN uv pip install --python /app/.venv/bin/python /build/dist/*.whl


# --- Runtime stage -----------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="headcleaner"
LABEL org.opencontainers.image.description="Walk a folder, convert every document to Markdown and/or OKF v0.2"
LABEL org.opencontainers.image.source="https://github.com/jamesdsizemore/headcleaner-cli"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Tesseract for OCR and libpst's readpst for full PST message extraction.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    pst-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy the venv from the builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Default to a TTY-friendly invocation
ENTRYPOINT ["headcleaner"]
CMD ["--help"]

# To bundle OfficeCLI for Office-format conversion:
#   1. Add to a derived image:
#        RUN apt-get install -y curl && \
#            curl -fsSL https://d.officecli.ai/install.sh | bash
#   2. Or mount from host:
#        docker run --rm \
#            -v /usr/local/bin/officecli:/usr/local/bin/officecli:ro \
#            -v /path/to/inbox:/inbox -v /path/to/out:/out \
#            headcleaner convert /inbox --output /out
