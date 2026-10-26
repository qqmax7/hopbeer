# План реализации SPEC-002: Вход через Yandex ID и самозапись пользователей

| Поле | Значение |
|---|---|
| Спека | [`spec.md`](./spec.md) |
| Статус | implemented |
| Автор | не назначен |
| Обновлено | 2026-10-26 |

План отвечает на вопрос «как», не добавляя новых требований. Если для
реализации нужно новое поведение — сначала оно появляется в `spec.md`.

## 1. Подход

Соцвход строится на django-allauth (MIT, версия 65.x; на 2026-10-26 актуальна
65.21.0 — установлена именно она; текущий стек — Python 3.11 локально и 3.12 на
проде (`docs/DEPLOYMENT.md:45`), Django 5.0.14 — удовлетворяет требованиям
библиотеки: Python 3.11+, Django 4.2+).
Провайдер `allauth.socialaccount.providers.yandex` уже содержит OAuth2-адаптер
(`oauth.yandex.com/authorize`, `oauth.yandex.ru/token`, `login.yandex.ru/info`) и
разбор профиля: `id` → uid, `default_email` → email, `display_name` → username,
`first_name`/`last_name` → имя.

Ключевые решения:

- **Старт входа — обычная GET-ссылка** (решение владельца 2026-10-26):
  `SOCIALACCOUNT_LOGIN_ON_GET = True`. У allauth по умолчанию старт требует
  POST, иначе клик по ссылке показал бы промежуточную страницу. Риск
  login-CSRF снижается проверкой `state` на callback (FR-010, §9 спеки).
- **Имя маршрута `login` сохраняется для совместимости**: в `beer_app/urls.py`
  перед `include('allauth.urls')` стоит `path('accounts/login/', account_views.login,
  name='login')`. Адрес и представление те же, что у `account_login`, но
  существующие тесты и `reverse('login')` продолжают работать без правок.
- **Прямой `/accounts/yandex/login/` без ключей** уводит на страницу входа:
  без `SocialApp` библиотека подняла бы исключение (500). Тонкая обёртка
  `brewery.views.yandex_login_start` проверяет `YANDEX_OAUTH_ENABLED`.
- **Перекрытие шаблонов** — через порядок `INSTALLED_APPS`: `brewery` стоит
  **раньше** приложений allauth, поэтому `brewery/templates/account/*` и
  `brewery/templates/socialaccount/*` находятся первыми (`APP_DIRS=True`).
  Шаблон `brewery/templates/registration/login.html` удалён после переезда.
- **Ошибки и отмена провайдера** не показываются отдельной технической
  страницей: адаптер в `on_authentication_error` пишет warning в лог, кладёт
  сообщение в `messages` и редиректит на страницу входа (гость) или на связи
  (вошедший). Шаблоны `authentication_error`/`login_cancelled` не нужны.
- **Список связей** отдаёт своё представление `brewery.views.ConnectionsView`
  (наследник штатного) — оно добавляет `socialaccounts` в контекст, а шаблон
  проекта рисует список, кнопку отвязки и пустое состояние.
- **Конфигурация провайдера — в настройках из окружения**, а не записью
  `SocialApp` в базе: `client_id`/`client_secret` читаются из переменных
  окружения и не дублируются в БД, админке и бэкапах (FR-012).
- **`/accounts/` переводится с `django.contrib.auth.urls` на `allauth.urls`**
  (`beer_app/urls.py:13`). Адреса `/accounts/login/` и `/accounts/logout/`
  сохраняются, меняются имена маршрутов: `login` → `account_login`,
  `logout` → `account_logout`. `LOGIN_URL`, `LOGIN_REDIRECT_URL`,
  `LOGOUT_REDIRECT_URL` (`beer_app/settings.py:206-208`) указывают на новые
  имена, поэтому редирект гостя и `next` не меняются (FR-001).
- **Самозапись открыта**: `SOCIALACCOUNT_AUTO_SIGNUP = True`,
  `SOCIALACCOUNT_EMAIL_REQUIRED = True`, `SOCIALACCOUNT_QUERY_EMAIL = True`
  (без email учётная запись не создаётся, FR-011). Роль не назначается, поэтому
  новый пользователь получает `is_staff = False` и матрицу прав `SPEC-001`
  (FR-003, FR-015).
- **Автопривязки по email нет**: `SOCIALACCOUNT_EMAIL_AUTHENTICATION = False`
  задаётся явно, хотя это и значение по умолчанию. Совпадение email приводит к
  странице дозаписи allauth (`socialaccount/signup.html`); её шаблон
  переопределяется, а адаптер запрещает создание второй учётной записи — вместо
  формы пользователь видит текст FR-006 и ссылку на вход. Точное поведение
  версии проверяется при реализации; если форма всё же позволяет ввести другой
  email, она закрывается адаптером.
- **Связи и привязка** — штатная страница allauth `socialaccount_connections`
  (`/accounts/3rdparty/`, в 65.x переехала из `/accounts/social/connections/`)
  с проектным шаблоном. Отвязка без рабочего пароля блокируется своим
  представлением на базе `ConnectionsView` (FR-009).
- **Логирование** — свой `SocialAccountAdapter` (`brewery/adapters.py`) для
  ошибок OAuth и конфликта email плюс сигналы `social_account_added` /
  `social_account_removed` для успешных сценариев; пишем в существующий логгер
  `brewery` (`beer_app/settings.py:196-200`), без токенов, кодов и секретов
  (FR-014).
- **Кнопка провайдера показывается только при заданных ключах**: флаг
  `YANDEX_OAUTH_ENABLED`, вычисляемый из наличия переменных окружения. Это
  делает локальную разработку, тесты и свежий клон работоспособными без ключей
  (FR-012, AC-016).
- **Учётные записи из соцвхода не имеют рабочего пароля** — штатное поведение
  allauth (`set_unusable_password()`), отдельного кода не требуется (FR-004).
- **Политика конфиденциальности** — обычное `TemplateView` без
  `LoginRequiredMixin` в `brewery/views.py`, маршрут `/privacy/` в
  `brewery/urls.py`, шаблон в стиле `brewery/base.html` (FR-013).
- **Шаблоны проекта переопределяют allauth**: `brewery` подключается в
  `INSTALLED_APPS` **раньше** приложений allauth, а не после: при `APP_DIRS=True`
  Django ищет шаблоны в порядке приложений, и первым должен быть `brewery`.
- **Регистрация по email и паролю не появляется**: адрес `/accounts/signup/`
  закрывается маршрутом-заглушкой перед `include('allauth.urls')` и ведёт на
  страницу входа (Non-goals спеки).

Рассмотренные и отклонённые альтернативы:

| Альтернатива | Почему отклонена |
|---|---|
| Своя реализация OAuth2 (state, обмен кода, профиль) | высокая цена ошибки в безопасности и десятки строк, которые allauth уже покрывает тестами; конституция V |
| Запись `SocialApp` в БД через админку | секреты уезжают в `db.sqlite3` и в бэкапы; конфигурация становится данными, а не окружением (конституция III) |
| `SOCIALACCOUNT_EMAIL_AUTHENTICATION = True` (автопривязка по email) | провайдер, ошибившийся с email, открывает чужую учётную запись; отклонено владельцем 2026-10-26 |
| Оставить `django.contrib.auth.urls` и добавить allauth рядом | два набора маршрутов `/accounts/…`, конфликт имён и шаблонов; проще один источник истины |
| Отключить локальный вход (`ACCOUNT_SOCIALACCOUNT_ONLY`) | ломает FR-001/FR-002 baseline и вход администратора, если у него нет Yandex |
| Google сразу | отклонено владельцем: сначала Yandex, Google — отдельная спека |
| Хранить токены провайдера (`SOCIALACCOUNT_STORE_TOKENS=True`) | токены не нужны приложению и являются лишними персональными данными (конституция III) |

## 2. Затрагиваемые файлы

| Файл | Изменение | AC |
|---|---|---|
| `requirements.txt` | `django-allauth[socialaccount]==65.21.0` (extra ставит `requests`, `oauthlib`, `PyJWT`; без extra не будет HTTP-клиента для обмена кода); установлено и проверено на Django 5.0.14 | AC-021 |
| `beer_app/settings.py` | `brewery` перед приложениями allauth (перекрытие шаблонов), затем `django.contrib.sites`, `allauth`, `allauth.account`, `allauth.socialaccount`, `allauth.socialaccount.providers.yandex`; `SITE_ID = 1`; `AUTHENTICATION_BACKENDS`; `allauth.account.middleware.AccountMiddleware`; `LOGIN_URL/LOGIN_REDIRECT_URL/LOGOUT_REDIRECT_URL` на `account_login`/`account_logout`; контекст-процессор `brewery.context_processors.yandex_oauth`; блок настроек allauth; `YANDEX_CLIENT_ID`/`YANDEX_CLIENT_SECRET` из окружения и `YANDEX_OAUTH_ENABLED` | AC-001…AC-003, AC-016 |
| `beer_app/urls.py` | `path('accounts/', include('allauth.urls'))` вместо `django.contrib.auth.urls`; перед include — совместимый `login`, обёртка `yandex_login_start` и `ConnectionsView`; `/accounts/signup/` — редирект на вход | AC-002, AC-003, AC-009, AC-016 |
| `brewery/adapters.py` | новый: `HopBeerSocialAccountAdapter` — запрет автопривязки и второй учётной записи при конфликте email, русский текст отвязки, логирование отказов и ошибок провайдера | AC-008, AC-012, AC-018 |
| `brewery/signals.py`, `brewery/apps.py` | новый: сигналы `user_logged_in`, `social_account_added`, `social_account_removed` → логгер `brewery` (успехи) | AC-019 |
| `brewery/context_processors.py` | новый: флаг `YANDEX_OAUTH_ENABLED` в шаблонах | AC-002, AC-016 |
| `brewery/views.py` | `yandex_login_start`, `ConnectionsView` (список связей в контексте), `PrivacyView` | AC-012, AC-016, AC-017 |
| `brewery/urls.py` | маршрут `/privacy/` (публичный) | AC-017 |
| `brewery/templates/account/login.html` | страница входа в стиле проекта: кнопка «Войти через Yandex ID» (по флагу), форма логина, ссылка на политику; заменяет `registration/login.html` | AC-002, AC-016, AC-017 |
| `brewery/templates/account/logout.html` | страница подтверждения выхода из allauth (POST-форма) | AC-023 |
| `brewery/templates/socialaccount/connections.html` | заголовок «Связи с аккаунтами», список связей, пустое состояние, кнопки подключения/отвязки | AC-009…AC-012 |
| `brewery/templates/socialaccount/messages/account_connected.txt`, `…/account_disconnected.txt` | тексты сообщений о подключении и отвязке из `spec.md` §6 | AC-010, AC-011 |
| `brewery/templates/brewery/base.html` | `{% url 'account_login' %}` / `account_logout`; имя пользователя — ссылка на страницу связей; блок `messages` | AC-002, AC-013, AC-023 |
| `brewery/templates/brewery/privacy.html` | новая страница политики конфиденциальности | AC-017 |
| `brewery/tests.py` | новые классы `YandexLoginTests`, `SocialAccountConnectionsTests`, `SocialLoginLoggingTests`, `PrivacyPolicyTests` | AC-001…AC-020, AC-022, AC-023 |
| `docs/DEPLOYMENT.md` | переменные окружения OAuth, callback URL, порядок выката и откат | AC-024 |
| `AGENTS.md` | конвенция: соцвход — через allauth, ключи только в окружении, тексты — в шаблонах проекта | — |
| `specs/backlog.md` | BL-09 → ссылка на `SPEC-002` | — |

`brewery/models.py`, `brewery/forms.py`, `brewery/admin.py` не меняются.
Шаблон `brewery/templates/registration/login.html` удаляется после переезда на
`account/login.html`.

## 3. Модель данных и миграции

- Своих моделей нет. Миграции приложений библиотеки создают таблицы
  `socialaccount_socialaccount`, `socialaccount_socialapp`,
  `socialaccount_socialtoken`, `account_emailaddress`,
  `account_emailconfirmation` и `django_site`.
- `SITE_ID = 1`; запись `django_site` создаётся миграцией `sites`. Домен в ней
  при конфигурации провайдера из настроек не используется для callback (он
  строится из запроса), но проверить на проде нужно — см. шаг 6 выката.
- `SOCIALACCOUNT_STORE_TOKENS = False` (значение по умолчанию): токены Yandex в
  базе не появляются.
- Обратимость: миграции allauth обратимы. Откат кода оставляет таблицы
  библиотеки — они не используются и не мешают; при желании удаляются
  `manage.py migrate socialaccount zero` / `account zero`. Учётные записи,
  созданные соцвходом, после отката остаются без пароля: администратор задаёт
  им пароль в `/admin/`, иначе люди потеряют доступ (FR-016).
- Перед выкатом обязателен бэкап `db.sqlite3` и `media/`
  (`docs/DEPLOYMENT.md:197-200`): впервые со времён baseline накатываются
  миграции новых приложений.

## 4. Маршруты, представления, формы

| Адрес | Имя маршрута | Назначение |
|---|---|---|
| `/accounts/login/` | `account_login` | вход по логину и паролю + кнопка Yandex (FR-001, FR-002) |
| `/accounts/logout/` | `account_logout` | выход POST-формой (FR-001, AC-023) |
| `/accounts/yandex/login/` | `yandex_login` | старт OAuth, в том числе `?process=connect` (FR-002, FR-008); без ключей — редирект на вход |
| `/accounts/yandex/login/callback/` | `yandex_callback` | callback провайдера (AC-003, AC-004) |
| `/accounts/3rdparty/` | `socialaccount_connections` | связи с аккаунтами (FR-007) |
| `/accounts/signup/` | `account_signup` | заглушка: редирект на вход (Non-goals) |
| `/accounts/password/change/`, `/accounts/password/reset/` | `account_change_password`, `account_reset_password` | стандартные страницы allauth вместо прежних django-auth |
| `/privacy/` | `privacy` | политика конфиденциальности (FR-013) |

Эскиз настроек:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    ...,
    'brewery',  # раньше allauth: шаблоны проекта перекрывают библиотечные
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.yandex',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',          # вход по паролю
    'allauth.account.auth_backends.AuthenticationBackend',  # соцвход
]

MIDDLEWARE = [
    ...,
    'allauth.account.middleware.AccountMiddleware',
]

LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'index'

YANDEX_CLIENT_ID = os.environ.get('YANDEX_CLIENT_ID', '')
YANDEX_CLIENT_SECRET = os.environ.get('YANDEX_CLIENT_SECRET', '')
YANDEX_OAUTH_ENABLED = bool(YANDEX_CLIENT_ID and YANDEX_CLIENT_SECRET)

SOCIALACCOUNT_PROVIDERS = {
    'yandex': {
        'APP': {'client_id': YANDEX_CLIENT_ID, 'secret': YANDEX_CLIENT_SECRET},
        'SCOPE': ['login:email', 'login:info'],
    },
}  # при выключенном флаге — пустой словарь, приложения провайдера нет
SOCIALACCOUNT_ADAPTER = 'brewery.adapters.HopBeerSocialAccountAdapter'
SOCIALACCOUNT_AUTO_SIGNUP = True          # самозапись без формы (FR-003)
SOCIALACCOUNT_EMAIL_REQUIRED = True       # без email учётка не создаётся (FR-011)
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False  # автопривязки по email нет (FR-006)
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_LOGIN_ON_GET = True         # старт входа — обычная GET-ссылка (FR-002)
ACCOUNT_EMAIL_VERIFICATION = 'none'       # почта не настроена
ACCOUNT_LOGIN_METHODS = {'username'}      # поведение входа как в baseline
ACCOUNT_LOGOUT_ON_GET = False             # выход только POST-формой
```

Проверки на сервере:

- `is_staff` новой учётной записи не выставляется ни в одном сценарии; права
  каталога и оценок — миксины `SPEC-001` (`brewery/views.py`), они не меняются.
- Отвязка Yandex проверяется на сервере в `DisconnectForm.clean` (allauth) плюс
  наш текст ошибки в `error_messages['no_password']`; скрытие кнопки — не защита.
- Кнопка Yandex в шаблоне управляется `YANDEX_OAUTH_ENABLED` (контекст-процессор
  `brewery.context_processors.yandex_oauth`); при выключенном флаге прямой
  `/accounts/yandex/login/` уводит на страницу входа: без `SocialApp` allauth
  поднял бы `SocialApp.DoesNotExist` → 500.
- Callback без валидного `state` (истёк, подделан, повторный) идёт тем же путём,
  что отмена: warning в лог и сообщение на странице входа.
- Конфликт email и отсутствие email проверяются в `pre_social_login` до создания
  пользователя; своя учётная запись из проверки исключена (подключение Yandex к
  ней не блокируется).

Запросы к базе: страница связей — одна выборка `SocialAccount` по
`request.user`; страница входа — без запросов к провайдеру; при соцвходе —
стандартные запросы allauth (поиск `SocialAccount`, `User`, запись связи).

## 5. Шаблоны и UI

- Имена шаблонов и маршрутов allauth сверены с установленной версией 65.21.0:
  `account/login.html`, `account/logout.html`, `socialaccount/connections.html`,
  `socialaccount/messages/*.txt`, маршруты `account_login`/`account_logout`,
  `yandex_login`/`yandex_callback`, `socialaccount_connections`. Шаблоны ошибок
  провайдера не нужны: адаптер уводит на страницу входа с сообщением.
- `account/login.html`: `<h1>Вход</h1>`, кнопка-ссылка «Войти через Yandex ID»
  (видна только при `YANDEX_OAUTH_ENABLED`), разделитель «или», поля «Имя
  пользователя»/«Пароль», кнопка «Войти», ссылки «Политика
  конфиденциальности» и «На главную». Ошибки формы — прежний текст «Неверное
  имя пользователя или пароль.».
- `socialaccount/connections.html`: заголовок «Связи с аккаунтами», блок
  «Подключённые аккаунты», строка «Yandex» с кнопкой «Отключить» либо кнопкой
  «Подключить Yandex ID»; пустое состояние «Пока нет подключённых аккаунтов.»;
  ссылка на политику. Список отдаёт `brewery.views.ConnectionsView`.
- `socialaccount/messages/account_connected.txt` и `…/account_disconnected.txt`:
  «Yandex ID подключён. Теперь можно входить одним нажатием.» и «Yandex ID
  отключён.» — штатные сообщения allauth заменяются проектом.
- Конфликт email и отсутствие email не доходят до формы дозаписи
  (`socialaccount/signup.html`): адаптер в `pre_social_login` кладёт сообщение
  («Аккаунт с таким email уже существует…», «Yandex не передал адрес
  электронной почты…») и уводит на страницу входа, где форма пароля рядом.
- `brewery/base.html`: `{% url 'account_login' %}`, `{% url 'account_logout' %}`,
  имя пользователя — ссылка на `{% url 'socialaccount_connections' %}`, блок
  `{% if messages %}` перед `{% block content %}` (все сообщения allauth и наши
  показываются в одном месте).
- `brewery/privacy.html`: разделы «Какие данные мы получаем», «Зачем они
  нужны», «Где они хранятся», «Чего мы не получаем», «Как удалить учётную
  запись», «Контакты»; текст без юридических обещаний сверх фактического
  поведения.
- Вёрстка: сообщения, ссылки-кнопки и список связей стилизованы минимально в
  `static/css/style.css`; мобильная шапка не меняется.

## 6. Тесты: карта AC → тест

Все тесты — в `brewery/tests.py`, декоратор
`@override_settings(STORAGES=TEST_STORAGES)` как в существующих классах.
Ключи провайдера подставляются в тестах константой `YANDEX_CREDENTIALS`
(`SOCIALACCOUNT_PROVIDERS={'yandex': {'APP': {'client_id': 'test-client-id',
'secret': 'test-secret'}}}`, `YANDEX_OAUTH_ENABLED=True`). Сеть не используется:
обмен кода на токен (`YandexOAuth2Adapter.get_access_token_data`) и HTTP-сессия
allauth (`HopBeerSocialAccountAdapter.get_requests_session`) подменяются
`unittest.mock`; профиль Yandex отдаёт `FakeYandexSession`. `state` берётся из
реального `GET /accounts/yandex/login/` тем же клиентом.

| AC | Тест | Класс | Тип |
|---|---|---|---|
| AC-001 | `test_guest_still_gets_login_redirect_with_next` | `YandexLoginTests` | Django TestCase |
| AC-002 | `test_login_page_shows_yandex_button_and_password_form` | `YandexLoginTests` | Django TestCase |
| AC-003 | `test_yandex_button_redirects_to_provider_with_state` | `YandexLoginTests` | Django TestCase |
| AC-004 | `test_first_yandex_login_creates_user_and_logs_in` | `YandexLoginTests` | Django TestCase |
| AC-005 | `test_social_user_has_no_usable_password` | `YandexLoginTests` | Django TestCase |
| AC-006 | `test_new_social_user_cannot_change_catalog` | `YandexLoginTests` | Django TestCase |
| AC-007 | `test_second_yandex_login_uses_same_account` | `YandexLoginTests` | Django TestCase |
| AC-008 | `test_existing_email_is_not_linked_automatically` | `YandexLoginTests` | Django TestCase |
| AC-009 | `test_guest_gets_login_redirect_for_connections_page` | `SocialAccountConnectionsTests` | Django TestCase |
| AC-010 | `test_authenticated_user_connects_yandex_and_signs_in_with_it` | `SocialAccountConnectionsTests` | Django TestCase |
| AC-011 | `test_user_with_password_can_disconnect_yandex` | `SocialAccountConnectionsTests` | Django TestCase |
| AC-012 | `test_user_without_password_cannot_disconnect_yandex` | `SocialAccountConnectionsTests` | Django TestCase |
| AC-013 | `test_provider_cancel_keeps_guest_on_login_page` | `YandexLoginTests` | Django TestCase |
| AC-014 | `test_provider_error_shows_message_not_500` | `YandexLoginTests` | Django TestCase |
| AC-015 | `test_missing_email_does_not_create_account` | `YandexLoginTests` | Django TestCase |
| AC-016 | `test_yandex_button_hidden_without_credentials` | `YandexLoginTests` | Django TestCase |
| AC-017 | `test_privacy_page_is_public_and_describes_data` | `PrivacyPolicyTests` | Django TestCase |
| AC-018 | `test_social_login_failure_is_logged_without_secrets` | `SocialLoginLoggingTests` | Django TestCase (`assertLogs('brewery', 'WARNING')`) |
| AC-019 | `test_social_login_success_is_logged` | `SocialLoginLoggingTests` | Django TestCase (`assertLogs('brewery', 'INFO')`) |
| AC-020 | `test_existing_user_keeps_password_login_after_migrations` | `YandexLoginTests` | Django TestCase |
| AC-021 | `makemigrations --check`, `check`, `migrate` на пустой БД | — | ручная проверка |
| AC-022 | `test_username_collision_creates_unique_username` | `YandexLoginTests` | Django TestCase |
| AC-023 | `test_social_user_can_log_out_with_post` | `YandexLoginTests` | Django TestCase |
| AC-024 | вход через Yandex на локальном сервере и на проде | — | ручная проверка |

- Проверяем код ответа, состояние БД (`User.objects.count()`,
  `SocialAccount.objects.filter(user=...)`, `has_usable_password()`), сессию
  (`_auth_user_id`) и наличие/отсутствие строк в HTML — не реализацию
  настроек.
- Тесты пишутся до реализации и должны падать по правильной причине: сейчас
  маршрутов `/accounts/yandex/…` нет, кнопки нет, страницы `/privacy/` нет.
- Данные фикстур: существующий пользователь с паролем и email
  `old@example.com`, второй пользователь, одно пиво и оценка существующего
  пользователя.
- Регрессия: существующие классы `BeerListRatingsTests`,
  `RatingListVisibilityTests`, `ReportViewTests`, `AccessMatrixTests` должны
  остаться зелёными без правок — они ловят поломку редиректа, `next`,
  шаблонов и прав после переезда на allauth.

## 7. Риски и откат

| Риск | Вероятность | Влияние | Смягчение |
|---|---|---|---|
| Переезд `/accounts/` на allauth ломает редирект гостя или `next` | средняя | высокое | AC-001, AC-003, AC-004; существующий `AccessMatrixTests` остаётся зелёным |
| Автопривязка по email всё же срабатывает в выбранной версии allauth | низкая | высокое (доступ к чужой учётной записи) | `SOCIALACCOUNT_EMAIL_AUTHENTICATION=False` явно + AC-008; ручная сверка настроек на выкате |
| Конфликт email приводит к форме дозаписи и лишней учётной записи | средняя | высокое | адаптер запрещает создание второй учётной записи и показывает текст FR-006; AC-008 |
| Пользователи, созданные соцвходом, теряют доступ при откате | средняя | среднее | FR-016: перед откатом администратор выдаёт пароли; шаг описан в `docs/DEPLOYMENT.md` |
| Секреты Yandex попадают в git или логи | низкая | высокое | только `os.environ`, `.env` на сервере; логи пишут провайдера и результат без токенов; AC-018 |
| Ошибка или таймаут Yandex показываются как 500 | средняя | среднее | AC-014, отдельные шаблоны ошибок; локальный вход не зависит от провайдера |
| Лимиты запросов allauth (`30/m/ip` на логин) мешают за NAT | низкая | низкое | при необходимости лимиты настраиваются `ACCOUNT_RATE_LIMITS`; отслеживать по логам |
| Шаблоны allauth в непереведённом виде попадают в интерфейс | средняя | низкое | шаблоны проекта переопределяют библиотечные, тексты — из §6 спеки; `brewery` в `INSTALLED_APPS` после allauth |
| Новая зависимость конфликтует с Django 5.0.14 или WhiteNoise | низкая | среднее | версия фиксируется в `requirements.txt`; `manage.py check` и тесты после установки |

План отката: `git revert` коммитов спеки и `pip install -r requirements.txt`
без allauth; таблицы библиотеки можно оставить (не используются) или удалить
`migrate account zero`/`socialaccount zero`. Данные каталога и оценок не
затрагиваются. Учётным записям, созданным соцвходом, администратор задаёт
пароль в `/admin/`. Конфигурация провайдера в `.env` удаляется, кнопка на
странице входа исчезает вместе с кодом.

## 8. Порядок выката

1. Зарегистрировать приложение на `https://oauth.yandex.com/client/new`
   (доступ к email и имени), указать callback URL
   `https://<прод-домен>/accounts/yandex/login/callback/` и локальный
   `http://127.0.0.1:8000/accounts/yandex/login/callback/`.
2. Положить `YANDEX_CLIENT_ID` и `YANDEX_CLIENT_SECRET` в `/opt/hopbeer/.env`
   (и в локальные переменные окружения); в git их не добавлять.
3. Сделать бэкап `db.sqlite3` и `media/`.
4. Ветка `kodik/spec-002-vhod-cherez-yandex-id`, реализация по `tasks.md`.
5. `manage.py test` и `manage.py check` — зелёные; `makemigrations --check` — без
   изменений схемы проекта; вручную проверить вход через настоящий Yandex ID
   локально (AC-024).
6. Выкат по `docs/DEPLOYMENT.md:182-189`: `git pull`,
   `pip install -r requirements.txt`, `migrate` (новые таблицы),
   `collectstatic --noinput`, `systemctl restart hopbeer`.
7. Проверить на проде: гость → редирект с `next`; вход по паролю; вход через
   Yandex; конфликт email; отмена на стороне Yandex; страница «Связи с
   аккаунтами»; `/privacy/`; отсутствие токенов и секретов в
   `journalctl -u hopbeer`.
8. Обновить `docs/DEPLOYMENT.md` (переменные окружения, callback, откат),
   закрыть BL-09 в `specs/backlog.md`, перевести спеку в `implemented`.

## Отступления от конституции

Нет. Новая зависимость django-allauth допустима по принципу V: собственная
реализация OAuth была бы дороже и рискованнее, а библиотека использует штатный
механизм Django (`django.contrib.auth`, сессии, шаблоны) без смены базы данных.
