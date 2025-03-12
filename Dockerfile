FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.docker.txt .
RUN pip install --no-cache-dir -r requirements.docker.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p data logs

# Make docker_main.py executable
RUN chmod +x docker_main.py

# Run as non-root user for better security
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

# Command to run the application using Docker-specific entry point
CMD ["python", "docker_main.py"]
