#!/bin/bash
set -e

echo "Starting the fixed Docker setup for NLP Web Scraper"

# Copy the fixed docker_main.py to replace the original
cp ./docker_helpers/fixed_docker_main.py ./docker_main.py
chmod +x ./docker_main.py

# Make sure directories exist
mkdir -p data logs docker_helpers

# Stop any running containers
echo "Stopping any running containers..."
docker-compose -f docker-compose.fixed.yml down --remove-orphans

# Build and run with the fixed docker-compose file
echo "Building and starting containers..."
docker-compose -f docker-compose.fixed.yml build
docker-compose -f docker-compose.fixed.yml up -d

echo "Containers are starting... waiting for them to initialize"
sleep 5

echo "Showing logs (press Ctrl+C to exit logs, containers will continue running)"
docker-compose -f docker-compose.fixed.yml logs -f
