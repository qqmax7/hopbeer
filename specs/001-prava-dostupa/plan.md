# План реализации SPEC-001: Разграничение прав доступа

| Поле | Значение |
|---|---|
| Спека | [`spec.md`](./spec.md) |
| Статус | in-progress |
| Автор | не назначен |
| Обновлено | 2026-10-26 |

План отвечает на вопрос «как», не добавляя новых требований. Если для
реализации нужно новое поведение — сначала оно появляется в `spec.md`.

## 1. Подход

Права выражаются двумя миксинами в `brewery/views.py`, поверх уже используемого
`LoginRequiredMixin`:

- `StaffOnlyMixin(LoginRequiredMixin, UserPassesTestMixin)` — для create/update/
  delete каталога. `test_func()` возвращает `request.user.is_staff`.
  Порядок базовых классов важен: `LoginRequiredMixin.handle_no_permission()`
  для анонимного пользователя делает редирект на вход, а для
  аутентифицированного без прав поднимает `PermissionDenied` → 403.
- `OwnRatingMixin` — для `RatingUpdateView` и `RatingDeleteView`: `get_queryset()`
  фильтрует по `owner=self.request.user`, поэтому чужая оценка даёт 404
  стандартным механизмом `get_object()`; в переопределённом `get_object()`
  отказ пишется в лог.

Матрица «роль → действие» закрывается этими двумя точками, потому что все
изменяющие представления уже собраны в одном файле и наследуются от generic
CBV: не нужно ни новых URL, ни форм, ни полей в моделях.

Рассмотренные и отклонённые альтернативы:

| Альтернатива | Почему отклонена |
|---|---|
| `permission_required('brewery.change_beer')` и права Django | требует выдавать права на каждую модель; для «администратор каталога» это лишняя настройка, а `is_staff` уже есть и уже управляет админкой |
| Собственная модель `Role`/поле `role` в профиле | новая сущность и миграция ради одного признака (конституция V) |
| Функциональные представления с ручными проверками | ломает принятую в проекте схему CBV |
| 403 на чужую оценку | раскрывает существование чужих оценок; приватность (конституция III) требует 404 |
| Скрывать кнопки без серверной проверки | не защита: прямой POST обойдёт |

## 2. Затрагиваемые файлы

| Файл | Изменение | AC |
|---|---|---|
| `brewery/views.py` | миксины `StaffOnlyMixin`, `OwnRatingMixin`; замена `LoginRequiredMixin` на `StaffOnlyMixin` в `Vendor/Hop/Beer` Create/Update/Delete (9 классов); `OwnRatingMixin` в `RatingUpdateView`, `RatingDeleteView`; логгер `brewery` | AC-003…AC-006, AC-009…AC-011, AC-013, AC-014, AC-016, AC-017 |
| `brewery/templates/403.html` | новая страница отказа с русским текстом | AC-015 |
| `brewery/templates/brewery/beer_list.html` | «Добавить пиво» и блок `.actions` — под `{% if user.is_staff %}` | AC-002, AC-007 |
| `brewery/templates/brewery/beer_detail.html` | кнопки «Изменить»/«Удалить» — под `{% if user.is_staff %}` | AC-002 |
| `brewery/templates/brewery/vendor_list.html` | «Добавить производителя» и `.actions` — под `{% if user.is_staff %}` | AC-018 |
| `brewery/templates/brewery/hop_list.html` | «Добавить хмель» и `.actions` — под `{% if user.is_staff %}` | AC-018 |
| `brewery/templates/brewery/rating_list.html` | блок `.actions` — под `{% if rating.owner_id == user.id %}` | AC-012 |
| `brewery/tests.py` | новый класс `AccessMatrixTests` | AC-001…AC-020 |
| `specs/backlog.md` | BL-10 → ссылка на `SPEC-001`, BL-01 сужается до `score` | — |
| `AGENTS.md` | конвенция: каталог правит только `is_staff`, оценки — только владелец | — |

Модели, формы, `brewery/urls.py`, `beer_app/*` не меняются.

## 3. Модель данных и миграции

- Схема не меняется: `makemigrations` не запускается, новых миграций нет.
- Роль — существующее поле `auth.User.is_staff`; существующие строки не
  переписываются, потери данных нет, бэкап перед выкатом не обязателен.
- Состав администраторов меняется вручную до рестарта: `is_staff = True`
  остаётся только у `admin` и `qqmax7`, у остальных снимается (FR-011,
  AC-021). Это одна операция в `/admin/` (или `User.objects.exclude(username__in=[...]).update(is_staff=False)`),
  а не миграция: меняется только флаг, пароли и остальные поля не трогаются.
- Откат не требует миграции назад: удаление кода возвращает прежнее поведение.

## 4. Маршруты, представления, формы

- URL-имена и маршруты не меняются (`brewery/urls.py` остаётся как есть).
- Миксины (эскиз):

```python
logger = logging.getLogger('brewery')


class StaffOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Вход обязателен; изменять каталог может только администратор."""

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            logger.warning(
                'Отказ в правах: %s %s (пользователь: %s)',
                self.request.method, self.request.path,
                self.request.user.get_username(),
            )
        return super().handle_no_permission()


class OwnRatingMixin:
    """Пользователь работает только со своими оценками; чужая — 404."""

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except Http404:
            logger.warning(
                'Чужая оценка недоступна: %s %s (пользователь: %s)',
                self.request.method, self.request.path,
                self.request.user.get_username(),
            )
            raise
```

- Представления: `VendorCreateView`, `VendorUpdateView`, `VendorDeleteView`,
  `HopCreateView`, `HopUpdateView`, `HopDeleteView`, `BeerCreateView`,
  `BeerUpdateView`, `BeerDeleteView` — первый базовый класс меняется на
  `StaffOnlyMixin`; `LoginRequiredMixin` из них убирается как избыточный.
  `BeerCreateView`/`BeerUpdateView` сохраняют `HopsJsonMixin` в MRO.
- `RatingUpdateView`, `RatingDeleteView` получают `OwnRatingMixin` до
  `UpdateView`/`DeleteView`; `RatingCreateView` не меняется (владельца
  по-прежнему задаёт `form_valid`), `RatingListView` — тоже (уже фильтрует).
- Валидация форм не меняется; `score` 1–10 — BL-01.
- Запросы к БД: `is_staff` берётся из `request.user` без запроса,
  `filter(owner=...)` использует существующий FK и не добавляет N+1.

## 5. Шаблоны и UI

- `brewery/templates/403.html` (в корне шаблонов приложения, поэтому находится
  через `APP_DIRS`):

```html
{% extends 'brewery/base.html' %}
{% block title %}Недостаточно прав{% endblock %}
{% block content %}
<h1>Недостаточно прав</h1>
<p>Изменять каталог может только администратор.</p>
<p><a class="button" href="{% url 'index' %}">← На главную</a></p>
{% endblock %}
```

- В шаблонах каталога оборачиваются только элементы управления: заголовки,
  данные и ссылки «Оценить» остаются у всех. Пример для списка пива:
  `{% if user.is_staff %}<div class="actions">…</div>{% endif %}`.
- Кнопки, которые сейчас рендерятся всегда, у пользователя просто исчезают;
  пустые `<div>` не остаются, чтобы вёрстка не «прыгала».
- Новых текстов, кроме страницы 403, нет; локализация и десятичный разделитель
  не затрагиваются.

## 6. Тесты: карта AC → тест

Все тесты — в `brewery/tests.py`, класс `AccessMatrixTests`
(`@override_settings(STORAGES=TEST_STORAGES)`), данные готовятся в `setUp`:
`user` (`is_staff=False`), `staff` (`is_staff=True`), `other`, по одному
пиву/хмелю/производителю и по оценке у `user` и `other`, плюс оценка с
`owner=None`.

| AC | Тест | Тип |
|---|---|---|
| AC-001 | `test_guest_is_redirected_to_login` | Django TestCase |
| AC-002 | `test_beer_list_hides_catalog_actions_for_user` | Django TestCase |
| AC-003 | `test_user_cannot_open_beer_edit` | Django TestCase |
| AC-004 | `test_user_cannot_delete_beer` | Django TestCase |
| AC-005 | `test_user_cannot_create_hop` | Django TestCase |
| AC-006 | `test_user_cannot_edit_or_delete_vendor` | Django TestCase |
| AC-007 | `test_staff_sees_catalog_actions` | Django TestCase |
| AC-008 | `test_staff_can_delete_beer` | Django TestCase |
| AC-009 | `test_user_cannot_change_beer` | Django TestCase |
| AC-010 | `test_user_cannot_open_foreign_rating_edit` | Django TestCase |
| AC-011 | `test_user_cannot_delete_foreign_rating` | Django TestCase |
| AC-012 | `test_owner_can_update_own_rating` | Django TestCase |
| AC-013 | `test_staff_cannot_edit_or_delete_foreign_rating_via_web` | Django TestCase |
| AC-014 | `test_guest_gets_login_redirect_for_rating_edit` | Django TestCase |
| AC-015 | `test_permission_denied_page_is_russian` | Django TestCase |
| AC-016 | `test_permission_denied_is_logged` | Django TestCase (`assertLogs('brewery', 'WARNING')`) |
| AC-017 | `test_ownerless_rating_is_unavailable_via_web` | Django TestCase |
| AC-018 | `test_lists_hide_catalog_actions_for_user` | Django TestCase |
| AC-019 | `manage.py makemigrations --check` + вход под существующим аккаунтом | ручная проверка |
| AC-020 | `test_user_cannot_reach_admin` | Django TestCase |
| AC-021 | `manage.py shell -c` → `['admin', 'qqmax7']` + вход под обоими аккаунтами | ручная проверка |

- Проверяем код ответа, изменение/неизменность БД (`refresh_from_db`,
  `assertFalse(Model.objects.filter(...).exists())`) и наличие/отсутствие
  строк в HTML — не реализацию миксинов.
- Тесты пишутся до реализации (этап 2 `tasks.md`) и должны падать по правильной
  причине: сейчас POST проходит, сейчас чужая оценка открывается.
- Регрессия ловится существующими `BeerListRatingsTests`, `RatingListVisibilityTests`,
  `ReportViewTests` — они должны остаться зелёными без правок.

## 7. Риски и откат

| Риск | Вероятность | Влияние | Смягчение |
|---|---|---|---|
| После выката кто-то из пользователей, кроме `admin` и `qqmax7`, теряет доступ к правке каталога | высокая (так решено) | среднее | осознанное решение владельца (FR-011); предупредить затронутых заранее, при необходимости роль возвращается в `/admin/` за секунды |
| Ошибка в MRO миксинов блокирует администратора | низкая | высокое | AC-007/AC-008 и ручная проверка под staff-аккаунтом |
| Гость получает 403 вместо редиректа на вход | низкая | среднее | AC-001, AC-014 |
| В логи попадают лишние данные | низкая | среднее | логируем только метод, путь и username |
| Администратору неудобно, что чужие оценки недоступны в вебе | средняя | низкое | правка через inline в `/admin/`; при необходимости — отдельная спека |
| Скрытые кнопки «съезжают» в вёрстке | низкая | низкое | ручной просмотр списков под обеими ролями |

План отката: `git revert` коммита спеки — миграций и изменений данных нет,
конфигурация и статика не меняются; после отката права снова определяются только
фактом входа.

## 8. Порядок выката

1. Убедиться, что `is_staff = True` только у `admin` и `qqmax7`, у остальных
   снять флаг (FR-011, AC-021); предупредить затронутых пользователей.
2. Создать ветку `kodik/spec-001-prava-dostupa`, реализовать по `tasks.md`.
3. `manage.py test` и `manage.py check` — зелёные; прогнать сценарии вручную
   под гостём, пользователем и администратором.
4. Выкатить по `docs/DEPLOYMENT.md` (`git pull`, `migrate` не нужен,
   `collectstatic` не нужен — новый шаблон не статика, `systemctl restart hopbeer`).
5. Проверить на проде: гость → редирект, пользователь → нет кнопок и 403 на
   прямой POST, администратор → правка каталога работает.
6. Закрыть BL-10 в `specs/backlog.md`, перевести спеку в `implemented`.

## Отступления от конституции

Нет.
