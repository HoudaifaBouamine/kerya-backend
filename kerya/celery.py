# kerya/celery.py
import os
from celery import Celery

# Default Django settings module for 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kerya.settings.prod")

app = Celery("kerya")

# Load config from Django settings, using namespace CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from installed apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
