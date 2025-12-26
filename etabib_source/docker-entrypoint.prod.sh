#!/bin/bash
# docker-entrypoint.prod.sh

# Wait for the database and Redis to be ready
echo "Waiting for database and Redis..."
while ! nc -z ${DB_HOST:-etabib_db} 3306; do
  sleep 1
done
while ! nc -z ${REDIS_HOST:-etabib_redis} 6379; do
  sleep 1
done

# Run Django migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application (use Daphne for ASGI apps)
echo "Starting application..."
exec "$@"
