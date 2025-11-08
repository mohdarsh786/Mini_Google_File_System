# Use Python 3.9 slim base image
FROM python:3.9-slim

# Set working directory inside container
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir cryptography

# Copy backend and web code into container
COPY backend/ /app/backend/
COPY web/ /app/web/

# Create data directories for master and chunk servers
RUN mkdir -p /data/master /data/chunks/text /data/chunks/images /data/chunks/documents /data/chunks/other

# Set Python output to unbuffered (for clean logs)
ENV PYTHONUNBUFFERED=1

# Expose all necessary ports (master, client, and chunks)
EXPOSE 8000 8001 9001 9002 9003

CMD ["python3", "-u"]