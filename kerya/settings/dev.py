from .base import *

DEBUG = True
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
STATIC_ROOT = "/app/static"
MEDIA_ROOT = "/app/media"
