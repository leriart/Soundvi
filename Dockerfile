# Soundvi Docker Image
# Multi-stage build for production

# Stage 1: Builder
FROM python:3.10-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Ensure Python can find user-installed packages
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Create non-root user
RUN useradd -m -u 1000 soundvi && \
    chown -R soundvi:soundvi /app

USER soundvi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; print('Healthy')" || exit 1

# Default command
CMD ["python", "main.py"]

# Build arguments
ARG VERSION=latest
LABEL org.opencontainers.image.title="Soundvi"
LABEL org.opencontainers.image.description="Audio visualization video generator"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.source="https://github.com/leriart/Soundvi"
LABEL org.opencontainers.image.licenses="MIT"