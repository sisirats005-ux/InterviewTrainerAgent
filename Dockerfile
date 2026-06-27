# Multi-stage lightweight base
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for compiling specific binary wheels if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source assets
COPY . .

# Create volume directories
RUN mkdir -p uploads vector_db static/charts

# Expose server port
EXPOSE 5000

# Set environment defaults
ENV FLASK_ENV=production

# Run with Gunicorn WSGI container
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
