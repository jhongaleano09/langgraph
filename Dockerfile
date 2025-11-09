FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libpq-dev \
        curl \
        build-essential \
        pkg-config \
        libcairo2-dev \
        libgirepository1.0-dev \
        libffi-dev \
        libglib2.0-dev \
        libpango1.0-dev \
        libgdk-pixbuf-xlib-2.0-dev \
        libgtk-3-dev \
        shared-mime-info \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml poetry.lock* ./

# Install poetry
RUN pip install poetry

# Configure poetry
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only=main --no-root

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p /app/generated_reports /app/logs /app/temp

# Make sure src is in Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]