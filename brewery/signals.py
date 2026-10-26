"""Журналирование соцвхода (SPEC-002 FR-014).

Пишем только провайдера, результат и имя пользователя. Токены, коды
авторизации, `client_secret` и содержимое профиля в лог не попадают.
"""
import logging

from allauth.account.signals import user_logged_in
from allauth.socialaccount.signals import social_account_added, social_account_removed
from django.dispatch import receiver

logger = logging.getLogger('brewery')


@receiver(user_logged_in)
def log_social_login(sender, request, user, sociallogin=None, **kwargs):
    """Успешный вход через провайдера виден в логгере `brewery`."""
    if sociallogin is None:
        return
    logger.info(
        'Вход через %s выполнен: %s',
        sociallogin.account.provider,
        user.get_username(),
    )


@receiver(social_account_added)
def log_social_account_added(sender, request, sociallogin, **kwargs):
    """Подключение Yandex к учётной записи."""
    logger.info(
        'Внешний аккаунт %s подключён: %s',
        sociallogin.account.provider,
        sociallogin.user.get_username(),
    )


@receiver(social_account_removed)
def log_social_account_removed(sender, request, socialaccount, **kwargs):
    """Отвязка Yandex от учётной записи."""
    if request is not None and request.user.is_authenticated:
        username = request.user.get_username()
    else:
        username = socialaccount.uid
    logger.info('Внешний аккаунт %s отключён: %s', socialaccount.provider, username)
