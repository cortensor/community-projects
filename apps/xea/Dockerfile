# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies (needed for compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY ./backend ./backend

# Create a non-root user for security (Render requirement)
RUN adduser --disabled-password --gecos '' xeauser
USER xeauser

# Expose port (Render listens on 10000 by default but we can config)
EXPOSE 8000

# Command to run the application
# We point to backend.app.main:app because of the directory structure
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT"]
