#!/bin/bash
set -e

echo "Waiting for database to be ready..."

MAX_TRIES=30
COUNT=0

until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' >/dev/null 2>&1 || [ $COUNT -eq $MAX_TRIES ]; do
  echo "Database is unavailable - sleeping (attempt $((COUNT+1))/$MAX_TRIES)"
  sleep 2
  COUNT=$((COUNT+1))
done

if [ $COUNT -eq $MAX_TRIES ]; then
  echo "ERROR: Database failed to become ready after $MAX_TRIES attempts"
  exit 1
fi

echo "Database is ready!"

# Check if this is a fresh database or needs reset
echo "Checking database state..."

# Function to check if a table exists
check_table_exists() {
    PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '$1');" | tr -d '[:space:]'
}

# Check for migration conflicts
if [ "$(check_table_exists 'django_migrations')" = "t" ]; then
    echo "Found existing django_migrations table."
    
    # Check if we have migration files
    MIGRATION_COUNT=$(find . -path "*/migrations/*.py" ! -name "__init__.py" 2>/dev/null | wc -l)
    
    if [ "$MIGRATION_COUNT" -eq 0 ]; then
        echo "No migration files found but database has existing migrations table."
        echo "This suggests migrations were deleted. Checking for custom tables..."
        
        # Check if custom tables exist
        CUSTOMER_EXISTS=$(check_table_exists 'customer')
        
        if [ "$CUSTOMER_EXISTS" = "f" ]; then
            echo "Custom tables don't exist either. Resetting database..."
            
            # Drop and recreate schema
            PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO $DB_USER;
            GRANT ALL ON SCHEMA public TO public;
            "
            echo "Database reset complete."
        else
            echo "Custom tables exist. Will try to sync migration state..."
        fi
    fi
fi

# Create migrations
echo "Creating migrations..."
python manage.py makemigrations --noinput

# Try to create migrations for specific apps if they exist
if [ -d "./customer" ] || python -c "import customer" 2>/dev/null; then
    echo "Creating customer app migrations..."
    python manage.py makemigrations customer --noinput || echo "Customer app migrations handled"
fi

# List available apps and create migrations for each
echo "Ensuring all installed app migrations are created..."
python -c "
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alemenosystem.settings')
import django
django.setup()
from django.conf import settings
for app in settings.INSTALLED_APPS:
    if not app.startswith('django.') and not app.startswith('rest_framework'):
        try:
            __import__(app + '.models')
            print(f'App with models: {app}')
        except ImportError:
            pass
" | while read -r line; do
    if [[ $line == App\ with\ models:* ]]; then
        app_name=$(echo "$line" | cut -d' ' -f4)
        echo "Creating migrations for $app_name..."
        python manage.py makemigrations "$app_name" --noinput || echo "Migrations for $app_name handled"
    fi
done

# Check migration status
echo "Checking migration status..."
python manage.py showmigrations

# Apply migrations
echo "Applying migrations..."
python manage.py migrate --noinput

# Verify critical tables exist before proceeding
echo "Verifying database tables..."
CUSTOMER_EXISTS=$(check_table_exists 'customer')
if [ "$CUSTOMER_EXISTS" = "f" ]; then
    echo "ERROR: Customer table still doesn't exist after migrations!"
    echo "Listing all tables in database:"
    PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "\dt"
    echo "Checking Django migration status:"
    python manage.py showmigrations
    echo "This indicates a problem with your Django models or migrations."
    echo "Please check your models.py files and ensure they are properly configured."
    exit 1
fi

echo "Database tables verified successfully!"

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Ingest initial data with error handling
echo "Ingesting initial data..."
if python manage.py ingest_initial_data; then
    echo "Initial data ingestion completed successfully!"
else
    echo "WARNING: Initial data ingestion failed. Application will start anyway."
    echo "You may need to manually create initial data."
fi

# Start app
echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 alemenosystem.wsgi:application