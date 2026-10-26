"""Адаптер django-allauth для входа через Yandex ID (SPEC-002).

Адаптер закрывает два сценария, которые библиотека по умолчанию ведёт на форму
дозаписи: конфликт email с существующей учётной записью (FR-006) и отсутствие
email от провайдера (FR-011). Вместо формы пользователь видит объяснение и
ссылку на вход по логину и паролю. Здесь же пишутся отказы соцвхода (FR-014).
"""
import logging

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger('brewery')

# Точные тексты из spec.md §6.
MSG_PROVIDER_FAILED = (
    'Вход через Yandex ID отменён или не удался. '
    'Попробуйте ещё раз или войдите по логину и паролю.'
)
MSG_EMAIL_TAKEN = (
    'Аккаунт с таким email уже существует. Войдите по логину и паролю, '
    'а затем подключите Yandex ID на странице «Связи с аккаунтами».'
)
MSG_EMAIL_MISSING = (
    'Yandex не передал адрес электронной почты. Войти можно по логину и паролю.'
)
MSG_PASSWORD_REQUIRED = 'Сначала задайте пароль — иначе вы не сможете войти.'


def _stop_target(request):
    """Куда вернуть пользователя после ошибки: гость — на вход, остальные — на связи."""
    if request.user.is_authenticated:
        return reverse('socialaccount_connections')
    return reverse('account_login')


class HopBeerSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Запрещает автопривязку по email и объясняет отказы по-русски."""

    error_messages = {
        **DefaultSocialAccountAdapter.error_messages,
        # Отвязка единственного способа входа (FR-009, AC-012).
        'no_password': MSG_PASSWORD_REQUIRED,
    }

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            # Учётная запись уже связана: дальше штатный вход или подключение.
            return
        provider = sociallogin.account.provider
        email = self._provider_email(sociallogin)
        if not email:
            logger.warning(
                'Соцвход не удался: провайдер=%s, результат=email_missing',
                provider,
            )
            raise self._stop(request, MSG_EMAIL_MISSING)
        if self._email_taken(email, request):
            logger.warning(
                'Соцвход не удался: провайдер=%s, результат=email_conflict',
                provider,
            )
            raise self._stop(request, MSG_EMAIL_TAKEN)

    def on_authentication_error(
        self, request, provider, error=None, exception=None, extra_context=None
    ):
        # В лог — только провайдер, код результата и класс ошибки. Токены, коды
        # авторизации и содержимое профиля сюда не попадают (FR-014).
        logger.warning(
            'Соцвход не удался: провайдер=%s, результат=%s, ошибка=%s',
            getattr(provider, 'id', provider),
            error or 'unknown',
            type(exception).__name__ if exception else 'нет',
        )
        raise self._stop(request, MSG_PROVIDER_FAILED)

    @staticmethod
    def _provider_email(sociallogin):
        """Email, который прислал провайдер: адрес из профиля или пустая строка."""
        email = ''
        if sociallogin.email_addresses:
            email = sociallogin.email_addresses[0].email
        if not email and sociallogin.user is not None:
            email = sociallogin.user.email or ''
        return email.strip()

    @staticmethod
    def _email_taken(email, request):
        """Email занят другой учётной записью? Своя учётная запись не конфликт."""
        users = get_user_model().objects.filter(email__iexact=email)
        if request.user.is_authenticated:
            users = users.exclude(pk=request.user.pk)
        return users.exists()

    @staticmethod
    def _stop(request, text):
        """Показать сообщение и увести со страницы ошибки обратно в приложение."""
        messages.error(request, text)
        return ImmediateHttpResponse(redirect(_stop_target(request)))
