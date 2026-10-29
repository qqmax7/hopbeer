"""
Django settings for beer_app project.

Адаптировано под SQLite (локальная разработка) вместо Supabase/PostgreSQL.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Безопасность: в продакшене SECRET_KEY, DEBUG и ALLOWED_HOSTS задаются через окружение
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

# В проде SECRET_KEY обязателен: без него приложение не стартует.
# Fallback с небезопасным ключом допустим только при DEBUG=True (локальная разработка).
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-key'
    else:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY не задан. Укажите его в переменных окружения.')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if os.environ.get('DJANGO_ALLOWED_HOSTS') else []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # brewery — раньше allauth, чтобы шаблоны проекта (account/*, socialaccount/*)
    # находились первыми и переопределяли библиотечные.
    'brewery',
    # Сайты и django-allauth: вход через Yandex ID (SPEC-002).
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.yandex',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'beer_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'brewery.context_processors.yandex_oauth',
            ],
        },
    },
]

WSGI_APPLICATION = 'beer_app.wsgi.application'


# База данных: SQLite (локально)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Медиафайлы (загруженные картинки пива)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# WhiteNoise — отдача статики в продакшене без nginx
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Безопасность
CSRF_TRUSTED_ORIGINS = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS') else []
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'False') == 'True'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Логирование.
# Пишем только в stdout/stderr: на сервере их собирает systemd-journald
# (`journalctl -u hopbeer`), он же сжимает и ротирует записи. Отдельные файлы
# не заводим — иначе нужен свой logrotate, а диск на сервере небольшой.
LOG_LEVEL = os.environ.get('DJANGO_LOG_LEVEL', 'INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
        # Такой же формат, каким Django печатает запросы в runserver.
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{server_time}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },
        'django.server': {
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        # Явно перекрываем стандартный django-логгер: по умолчанию при DEBUG=False
        # он отправляет ошибки письмом через AdminEmailHandler, а почта не настроена.
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # django.request пишет 4xx как WARNING, 5xx как ERROR с traceback —
        # именно эти записи нужны, чтобы разбирать ошибки на проде.
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Печать запросов при локальном `manage.py runserver` (на проде этот логгер
        # не используется — там запросы пишет gunicorn).
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
        # Логи приложения: logger = logging.getLogger(__name__) в brewery.*
        'brewery': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}


# Аутентификация
LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'


# Вход через Yandex ID (SPEC-002).
# Ключи приложения Yandex — только из окружения: в репозитории, БД и логах их нет.
YANDEX_CLIENT_ID = os.environ.get('YANDEX_CLIENT_ID', '')
YANDEX_CLIENT_SECRET = os.environ.get('YANDEX_CLIENT_SECRET', '')
# Флаг доступности OAuth; кнопка входа показывается и без ключей, но старт
# OAuth без них возвращает понятную ошибку, а не техническую страницу.
YANDEX_OAUTH_ENABLED = bool(YANDEX_CLIENT_ID and YANDEX_CLIENT_SECRET)

if YANDEX_OAUTH_ENABLED:
    SOCIALACCOUNT_PROVIDERS = {
        'yandex': {
            'APP': {
                'client_id': YANDEX_CLIENT_ID,
                'secret': YANDEX_CLIENT_SECRET,
            },
            'SCOPE': ['login:email', 'login:info'],
        },
    }
else:
    SOCIALACCOUNT_PROVIDERS = {}

SOCIALACCOUNT_ADAPTER = 'brewery.adapters.HopBeerSocialAccountAdapter'
SOCIALACCOUNT_AUTO_SIGNUP = True          # самозапись без формы (FR-003)
SOCIALACCOUNT_EMAIL_REQUIRED = True       # без email учётная запись не создаётся (FR-011)
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False  # автопривязки по email нет (FR-006)
SOCIALACCOUNT_STORE_TOKENS = False          # токены Yandex в базе не храним
# Старт входа — обычная GET-ссылка (решение владельца 2026-10-26).
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_EMAIL_VERIFICATION = 'none'         # почта не настроена
ACCOUNT_LOGIN_METHODS = {'username'}        # вход по логину, как в baseline
ACCOUNT_LOGOUT_ON_GET = False               # выход только POST-формой