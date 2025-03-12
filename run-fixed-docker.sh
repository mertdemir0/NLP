#!/bin/bash
set -e

echo "Starting the fixed Docker setup for NLP Web Scraper"

# Copy the modified docker_main.py to the root directory
cp ./docker_helpers/modified_docker_main.py ./docker_main.py

# Make sure docker_helpers directory exists in the container
mkdir -p data logs

# Build and run with the fixed docker-compose file
echo "Building and starting containers..."
docker-compose -f docker-compose.fixed.yml down --remove-orphans
docker-compose -f docker-compose.fixed.yml build
docker-compose -f docker-compose.fixed.yml up -d

echo "Containers are starting... waiting for them to initialize"
sleep 5

echo "Showing logs (press Ctrl+C to exit logs, containers will continue running)"
docker-compose -f docker-compose.fixed.yml logs -f
