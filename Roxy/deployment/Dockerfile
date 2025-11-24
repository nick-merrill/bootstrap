# Dockerfile for Roxy Monitor
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./
COPY config_advanced.yaml ./

# Create alerts directory
RUN mkdir -p /app/alerts

# Run as non-root user
RUN useradd -m -u 1000 roxy && \
    chown -R roxy:roxy /app
USER roxy

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)"

# Run the monitor
CMD ["python3", "roxy_monitor.py"]
