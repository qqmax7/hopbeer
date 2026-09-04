"""ASGI-конфигурация для проекта beer_app."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beer_app.settings')

application = get_asgi_application()