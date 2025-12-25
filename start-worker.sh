#!/bin/bash
# Start script for Celery worker service

set -e  # Exit on error

echo "⚙️ Starting Celery Worker..."
echo "📊 Configuration:"
echo "   - App: fxfront"
echo "   - Concurrency: 2"
echo "   - Log Level: info"

# Start Celery Worker
exec celery -A fxfront worker --loglevel=info --concurrency=2
