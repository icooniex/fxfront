"""
Celery Configuration for FX Trading Application

This module sets up Celery with Redis as both broker and result backend.
"""

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fxfront.settings')

app = Celery('fxfront')

# Using Redis as broker and result backend from settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Import simple tasks explicitly
app.autodiscover_tasks(['trading'], related_name='tasks_simple')


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery setup"""
    print(f'Request: {self.request!r}')
