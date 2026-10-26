# HopBeer — база данных пивоварни

Веб-приложение на Django для ведения базы данных пива, хмеля, производителей и оценок.
Формы заполнения данных сохраняются в локальную базу **SQLite**.

Проект ведётся по спецификациям: см. раздел [Spec-driven development](#spec-driven-development).

## Возможности

- CRUD для сущностей: **Пиво**, **Хмель**, **Производители**, **Оценки**.
- Страница **Отчет**: топ-5 хмелей по средней оценке и топ-5 производителей по количеству пива.
- Админ-панель Django.
- Локальная база данных SQLite (без внешних сервисов).

## Установка и запуск

```bash
# 1. Создать и активировать виртуальное окружение
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Применить миграции
python manage.py migrate

# 4. Запустить сервер
python manage.py runserver
```

Откройте http://127.0.0.1:8000/ — главная страница со ссылками на все разделы.

## Тесты

```powershell
$env:DJANGO_DEBUG = 'True'
.venv\Scripts\python.exe manage.py test
```

## Spec-driven development

Изменения начинаются со спецификации: поведение, требования и критерии приёмки
описываются до кода, а тесты доказывают выполнение критериев.

- `specs/README.md` — процесс: жизненный цикл, статусы, Definition of Ready/Done.
- `specs/constitution.md` — принципы проекта.
- `specs/000-baseline/spec.md` — текущее поведение (as-is), точка отсчёта.
- `specs/backlog.md` — очередь изменений и известных долгов.
- `AGENTS.md` — правила работы для ИИ-агентов и людей.

Новая доработка:

```powershell
.venv\Scripts\python.exe scripts/new_spec.py --title "Поиск по пиву"
```

Скрипт создаёт `specs/NNN-<slug>/` с `spec.md`, `plan.md`, `tasks.md`. Дальше
спека заполняется, проходит ревью, и только после этого пишется код.

## Структура

```
hopbeer/
├── beer_app/          # настройки проекта
├── brewery/           # приложение (модели, формы, представления, шаблоны)
├── specs/             # конституция, baseline, спеки, шаблоны, бэклог
├── scripts/           # импорт данных, создание спек
├── static/            # статические файлы (CSS)
├── docs/              # документация (в т.ч. DEPLOYMENT.md)
├── deploy/            # скрипты развёртывания
├── AGENTS.md          # правила работы в репозитории
├── manage.py
└── requirements.txt
```