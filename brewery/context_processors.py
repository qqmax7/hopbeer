"""Контекст шаблонов приложения brewery."""
from django.conf import settings


def yandex_oauth(request):
    """Флаг «вход через Yandex ID настроен» для шаблонов (SPEC-002 FR-012)."""
    return {'YANDEX_OAUTH_ENABLED': getattr(settings, 'YANDEX_OAUTH_ENABLED', False)}
