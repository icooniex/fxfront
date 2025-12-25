web: chmod +x migrate.sh && ./migrate.sh && gunicorn fxfront.wsgi --config gunicorn.conf.py --log-file -
worker: celery -A fxfront worker --loglevel=info --concurrency=2
beat: celery -A fxfront beat --loglevel=info

