"""Корневые URL-маршруты проекта beer_app."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

from allauth.account import views as account_views

from brewery import views as brewery_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('brewery.urls')),
]

urlpatterns += [
    # Маршруты django-allauth: вход, выход, связи с аккаунтами, провайдер Yandex.
    # Свои маршруты идут раньше include, чтобы перекрывать библиотечные.
    # Имя `login` сохранено для совместимости: на него ссылаются шаблоны и тесты,
    # написанные до переезда на allauth (SPEC-002 FR-001).
    path('accounts/login/', account_views.login, name='login'),
    # Без ключей старт OAuth возвращает на страницу входа с сообщением об ошибке (FR-010).
    path('accounts/yandex/login/', brewery_views.yandex_login_start, name='yandex_login'),
    # Связи с аккаунтами: своё представление добавляет список связей в контекст.
    path(
        'accounts/3rdparty/',
        brewery_views.ConnectionsView.as_view(),
        name='socialaccount_connections',
    ),
    # Регистрация по логину и паролю не открывается (Non-goals SPEC-002).
    path(
        'accounts/signup/',
        RedirectView.as_view(pattern_name='account_login', permanent=False),
        name='account_signup',
    ),
    path('accounts/', include('allauth.urls')),
]

# Отдача медиафайлов (загруженные картинки пива) в dev-режиме
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
