#!/bin/bash
set -e

PORT=${PORT:-6543}

# Patch the port in production.ini at runtime
sed -i "s|listen = 0.0.0.0:6543|listen = 0.0.0.0:${PORT}|g" production.ini

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Starting server on port ${PORT}..."
exec pserve production.ini
