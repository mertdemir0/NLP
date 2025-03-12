# Docker Integration for NLP Project

This guide explains how to use Docker with your NLP web scraping application.

## Files Created

1. **Dockerfile**: Contains instructions to build the Docker image for your application
2. **docker-compose.yml**: Configures your application and the Splash service needed for web scraping
3. **docker_config.py**: Helper module with Docker-specific configurations
4. **docker_main.py**: Docker-compatible entry point that runs your application in a containerized environment
5. **.dockerignore**: Specifies files that should be excluded from the Docker context

## Getting Started

### Replace the Dockerfile

The new Dockerfile is currently saved as `Dockerfile.new`. You need to replace the original file:

```bash
mv Dockerfile.new Dockerfile
```

### Build and Run with Docker Compose

```bash
# Build and start the containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

## Configuration

You can customize the application's behavior through environment variables in the `docker-compose.yml` file:

- `SPLASH_URL`: URL for the Splash service (default: http://splash:8050)
- `MAX_RESULTS`: Maximum number of articles to collect per day (default: 20)
- `START_DATE`: Start date for article collection (default: 2020-01-01)
- `END_DATE`: End date for article collection (default: current date)
- `DATA_DIR`: Directory for storing data (default: /app/data)
- `LOG_LEVEL`: Logging level (default: INFO)
- `RETRY_TIMES`: Number of retry attempts (default: 3)
- `DOWNLOAD_TIMEOUT`: Timeout for downloads in seconds (default: 90)
- `MIN_DELAY`/`MAX_DELAY`: Range for random delay between requests (default: 120-180 seconds)

## Data Persistence

Data is stored in the `./data` directory on your host machine, which is mounted to `/app/data` in the container. This ensures that your database and other data files persist even if the container is removed.

Logs are stored in the `./logs` directory.

## How It Works

The Docker setup uses your existing `main.py` code without modification. Instead, it:

1. Uses `docker_main.py` as the entry point
2. Imports functionality from your original `main.py`
3. Enhances it with Docker-specific features like environment variables and signal handling
4. Connects to the Splash service using Docker's internal networking

This approach allows you to continue developing your original code without Docker-specific changes while still enjoying the benefits of containerization.
