# Развёртывание hopbeer + Telegram WEB-прокси (tproxy-server)

Отчёт о проделанной работе: `max.evgdan.ru`.

## 1. Что сделано

На сервере `max.evgdan.ru` (Ubuntu 24.04, 1 CPU, 1 ГБ RAM) параллельно работают два сервиса:

1. **Web-приложение hopbeer** (Django + gunicorn + SQLite) — база данных пивоварни.
2. **Telegram WEB-прокси (tproxy-server)** — официальный proof-of-concept от Telegram Desktop,
   «замаскированный» под тот же сайт: по адресу `max.evgdan.ru` и с секретом работает прокси для Telegram,
   а обычные посетители видят обычный сайт hopbeer.

Никаких дополнительных DNS-записей не потребовалось — прокси использует **тот же домен** `max.evgdan.ru`,
что и сайт. Это и есть задуманная схема «скрытого» прокси.

## 2. Схема работы

```
Интернет
   │  :80 / :443  (только Caddy)
   ▼
Caddy 2.11.4  (TLS, сертификаты Let's Encrypt, редиректы)
   │
   └──► tproxy-server (реле, 127.0.0.1:8080) ──► надежно закрыто навне
          │  ├─ запрос с валидным «мостом» (Telegram-клиент со секретом)
          │  │      └──► MTProxy (официальный, 127.0.0.1:2398) ──► Telegram
          │  └─ обычный запрос (браузер, сканер)
          │         └──► hopbeer (gunicorn, 127.0.0.1:8000) ──► SQLite
          └─ admin-эндпоинты (127.0.0.1:8081) — только локально
```

Ключевые принципы (по докам tproxy-server):

- Реле **не расшифровывает** MTProxy-трафик — оно лишь проксирует TCP-стримы как есть.
- Профиль реле содержит **тот же секрет**, что и MTProxy: клиент приходит со `https://max.evgdan.ru/?bridge=<секрет>`,
  получает один раз мост (bridge page) и работает как через обычный MTProxy.
- Запросы **без** корректного моста (в т.ч. `?bridge=wrong`) возвращают обычный сайт hopbeer — прокси не выделяется.

## 3. Что именно было установлено и настроено на сервере

### Веб-приложение hopbeer (уже работало ранее, сохранено)

- Код: `/opt/hopbeer` (клон `https://github.com/qqmax7/hopbeer.git`, ветка `master`).
- Виртуальное окружение: `/opt/hopbeer/venv` (Python 3.12, Django 5.0.14).
- БД: SQLite `/opt/hopbeer/db.sqlite3`.
- gunicorn как systemd-сервис: `hopbeer.service` (`127.0.0.1:8000`, 2 воркера).
- Конфигурация через переменные окружения: `/opt/hopbeer/.env`
  (секрет ключа, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`).

### Telegram WEB-прокси (tproxy-server)

- **Go 1.26.5** — `/opt/go` (используется только для сборки).
- **Реле**: собран из `https://github.com/telegramdesktop/tproxy-server` (коммит `f7a6acc`)
  в `/usr/local/bin/tproxy-server`; исходники — `/opt/tproxy-server`.
- **MTProxy**: официальный (закреплённый коммит репозитория Telegram), собран и установлен как `mtproxy`-юзер;
  слушает `127.0.0.1:2398`; секреты и конфиг в `/etc/mtproxy/` (`proxy-secret`, `proxy-multi.conf`, `mtproxy.env`).
- **Конфигурация реле**: `/etc/tproxy-server/config.json` (+ `profiles.json` с секретом, права `0400`,
  подгружается через systemd `LoadCredential`; токен-ключ `/etc/tproxy-server/token.key`).
- **systemd-сервисы** (все `enabled` + `active`):
  - `tproxy-server.service` — реле, слушает `127.0.0.1:8080` (сайт/мост) и `127.0.0.1:8081` (health).
  - `mtproxy.service` — официальный MTProxy на `127.0.0.1:2398`.
  - `tproxy-firewall.service` — nftables-правило: закрывает `2398` и `8888` от внешнего мира.
  - `refresh-mtproxy-config.{service,timer}` — ежедневное обновление `proxy-multi.conf`.
- **Caddy 2.11.4** — заменил nginx на внешних портах `80/443`:
  - сам получает и продлевает сертификаты Let's Encrypt (ACME-контакт `admin@evgdan.ru`);
  - `max.evgdan.ru` проксируется на реле (`127.0.0.1:8080`), реле — на gunicorn (`127.0.0.1:8000`);
  - `www.max.evgdan.ru` → 301 на `max.evgdan.ru`;
  - `http://` → 308 на `https://`.
  - Конфиг: `/etc/caddy/Caddyfile` (таймауты и настройки — по докам tproxy-server, HSTS включён).
- **nginx** остановлен и отключён (конфигурации сохранены в `/etc/nginx/`).

## 4. Как это использовать

### Секрет прокси

Секрет сгенерирован один раз случайным образом (32 hex). Он хранится ТОЛЬКО на сервере
(`/etc/mtproxy/mtproxy.env` и `/etc/tproxy-server/profiles.json`), в репозиторий не попадает.
При необходимости его можно поменять: обновить оба файла и перезапустить `tproxy-server` и `mtproxy`.
**Не публикуйте секрет в открытых источниках** — иначе прокси перестанет быть скрытым.

### Подключение в Telegram

В Telegram: Настройки → Данные и хранение → Прокси → Добавить прокси → Тип **WEB**.

- **Хост (server):** `max.evgdan.ru`
- **Порт:** 443
- **Секрет:** (ваш секрет, 32 hex-символа)

Либо открыть ссылку вида:

```
https://t.me/webproxy?server=max.evgdan.ru&secret=ВАШ_СЕКРЕТ
```

Поддерживаемые клиенты (proof-of-concept): Telegram Desktop, экспериментальный Android/iOS.

Просто откройте сайт `https://max.evgdan.ru/` в браузере — вы увидите обычный сайт hopbeer.

## 5. Проверка результата

Все проверки выполнены **после** развёртывания (снаружи и изнутри):

| Проверка | Результат |
|---|---|
| `curl https://max.evgdan.ru/` | **200** (страница hopbeer) |
| `curl https://max.evgdan.ru/admin/login/` | **200** |
| `curl https://max.evgdan.ru/static/css/style.css` | **200** |
| `curl https://www.max.evgdan.ru/` | **301** → `https://max.evgdan.ru/` |
| `curl http://max.evgdan.ru/` | **308** → `https://max.evgdan.ru/` |
| `curl 'https://max.evgdan.ru/?bridge=wrong'` | **200** (та же страница hopbeer — прикрытие работает) |
| `curl 'https://max.evgdan.ru/?bridge=<секрет>'` | **200** (отдаётся мост — прокси активно) |
| Внешние порты `8080`, `8081`, `2398`, `8888` | **closed** снаружи |
| Сертификат Let's Encrypt | выдан на `max.evgdan.ru` и `www.max.evgdan.ru` |
| `systemctl is-active caddy tproxy-server mtproxy tproxy-firewall hopbeer` | все **active** |
| nftables-правило после `restart nftables` | таблица переприменяется автоматически |
| Сервисы при перезагрузке | все `enabled` (автозапуск) |

## 6. Обслуживание

### Проверить статус

```bash
systemctl --no-pager --full status caddy tproxy-server mtproxy tproxy-firewall hopbeer
systemctl is-active refresh-mtproxy-config.timer
```

### Логи

```bash
journalctl -u caddy -u tproxy-server -u mtproxy --since '30 minutes ago'
```

### Рестарт прокси (обрыв сессий — нормально, клиент переподключится)

```bash
systemctl restart tproxy-server mtproxy
```

### Обновление hopbeer после пуша в GitHub

```bash
cd /opt/hopbeer && git pull && ./venv/bin/pip install -r requirements.txt && \
./venv/bin/python manage.py migrate && \
./venv/bin/python manage.py collectstatic --noinput && \
systemctl restart hopbeer
```

### Обновление реле tproxy-server

```bash
cd /opt/tproxy-server && sudo ./deploy/update-relay.sh
```

### Резервное копирование

Минимум: `/opt/hopbeer/db.sqlite3` и `/etc/tproxy-server/`, `/etc/mtproxy/`,
`/etc/caddy/Caddyfile`, `/opt/hopbeer/.env`.

## 7. Файлы конфигурации на сервере

| Путь | Назначение |
|---|---|
| `/etc/caddy/Caddyfile` | веб-шлюз: домены, TLS, прокси на реле |
| `/etc/tproxy-server/config.json` | конфигурация реле (публичный домен, upstream на gunicorn) |
| `/etc/tproxy-server/profiles.json` | секрет + backend-адрес MTProxy (права `0400`) |
| `/etc/tproxy-server/token.key` | токен-ключ реле (резервировать, не менять) |
| `/etc/mtproxy/mtproxy.env` | секрет MTProxy + workers/connections |
| `/etc/mtproxy/proxy-secret`, `proxy-multi.conf` | официальные данные MTProxy (обновляются таймером) |
| `/etc/systemd/system/*.service`, `*.timer` | все юниты (tproxy, mtproxy, firewall, refresh, caddy, hopbeer) |
| `/opt/hopbeer/.env` | переменные окружения Django |
| `/opt/hopbeer/db.sqlite3` | база данных приложения |