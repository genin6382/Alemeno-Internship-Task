# In alemenosystem/celery.py
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alemenosystem.settings')

app = Celery('alemenosystem')
app.config_from_object('django.conf:settings', namespace='CELERY')

# This discovers tasks from all installed apps
app.autodiscover_tasks()