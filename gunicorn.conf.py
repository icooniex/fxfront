"""
Gunicorn configuration for production deployment.
Optimized for Railway/cloud deployment with SSL/TLS support.
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WEB_CONCURRENCY', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeouts - Increased to prevent SSL handshake timeouts
timeout = 120  # Worker timeout (increased from default 30s)
graceful_timeout = 30
keepalive = 5  # Keep-alive connections to reduce SSL handshake overhead

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'fxfront_gunicorn'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL - For handling SSL termination from reverse proxy
forwarded_allow_ips = '*'
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Preload app for better performance
preload_app = True

# Reload on code change (disable in production)
reload = os.getenv('DEBUG', 'False') == 'True'
