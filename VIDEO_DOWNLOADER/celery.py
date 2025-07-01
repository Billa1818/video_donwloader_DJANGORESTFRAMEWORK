import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VIDEO_DOWNLOADER.settings')

app = Celery('VIDEO_DOWNLOADER')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'cleanup-old-downloads-every-3h': {
        'task': 'downloader.tasks.cleanup_old_downloads',
        'schedule': crontab(minute=0, hour='*/3'),
    },
} 