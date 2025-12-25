#!/bin/bash
# Start script for Django web service

set -e  # Exit on error

echo "🚀 Starting Django Web Service..."

# Run migrations
echo "📦 Running database migrations..."
chmod +x migrate.sh
./migrate.sh

# Start Gunicorn
echo "🌐 Starting Gunicorn..."
exec gunicorn fxfront.wsgi --config gunicorn.conf.py --log-file -
