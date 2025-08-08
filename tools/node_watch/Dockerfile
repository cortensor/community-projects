# File: Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Install only Python dependencies needed by the watcher
COPY requirements.txt ./
RUN pip install --no-cache-dir docker requests

# Copy application code
COPY . /app

# Default command
CMD ["python", "main.py"]
