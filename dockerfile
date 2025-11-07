FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy backend files
COPY backend/ /app/backend/

# Copy web files
COPY web/ /app/web/

# Create data directories
RUN mkdir -p /data/master /data/chunks

# Set Python to unbuffered mode
ENV PYTHONUNBUFFERED=1

# Default command (will be overridden in docker-compose)
CMD ["python3", "-u"]