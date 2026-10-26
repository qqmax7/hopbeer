"""Конфигурация приложения brewery."""
from django.apps import AppConfig


class BreweryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'brewery'

    def ready(self):
        # Подключаем обработчики сигналов соцвхода (SPEC-002 FR-014).
        from . import signals  # noqa: F401
