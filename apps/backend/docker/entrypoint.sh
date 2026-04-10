#!/bin/sh
set -e

cd /app

echo "Running migrations..."
/app/.venv/bin/alembic upgrade head

echo "Starting $*..."
exec "$@"
