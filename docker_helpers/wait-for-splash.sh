#!/bin/bash
set -e

HOST="splash"
PORT="8050"
TIMEOUT=60
RETRY_INTERVAL=2

echo "Waiting for Splash service at $HOST:$PORT..."
start_time=$(date +%s)

until curl -s "http://$HOST:$PORT/_ping" > /dev/null || [ $(($(date +%s) - start_time)) -gt $TIMEOUT ]; do
  echo "Splash is unavailable - retrying in $RETRY_INTERVAL seconds..."
  sleep $RETRY_INTERVAL
done

if [ $(($(date +%s) - start_time)) -gt $TIMEOUT ]; then
  echo "Timed out waiting for Splash after $TIMEOUT seconds"
  exit 1
fi

echo "Splash is up and running!"
exec "$@"
