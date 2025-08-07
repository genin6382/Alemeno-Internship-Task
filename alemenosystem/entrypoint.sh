#!/bin/bash
set -e

echo "Waiting for database to be ready..."

MAX_TRIES=30
COUNT=0

until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' >/dev/null 2>&1 || [ $COUNT -eq $MAX_TRIES ]; do
  echo "Database is unavailable - sleeping ($((COUNT+1))/$MAX_TRIES)..."
  sleep 2
  COUNT=$((COUNT+1))
done

if [ $COUNT -eq $MAX_TRIES ]; then
  echo "ERROR: Database failed to become ready."
  exit 1
fi

echo "Database is ready!"

echo "Running migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Ingesting initial data..."
python manage.py ingest_initial_data

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 alemenosystem.wsgi:application
