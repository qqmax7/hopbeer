"""Тесты списка пива и отображения оценок."""
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import requests
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.yandex.views import YandexOAuth2Adapter
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .adapters import HopBeerSocialAccountAdapter
from .models import Beer, Hop, Rating, Vendor

User = get_user_model()

# В продакшене статика собирается через collectstatic (CompressedManifestStaticFilesStorage);
# в тестах манифеста нет, поэтому берём обычное хранилище.
TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'
    },
}


@override_settings(STORAGES=TEST_STORAGES)
class BeerListRatingsTests(TestCase):
    def setUp(self):
        self.me = User.objects.create_user(username='me', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.beer = Beer.objects.create(name='Fruitality', style='Fruited Milk IPA')
        self.empty_beer = Beer.objects.create(name='Boring Lager')
        Rating.objects.create(beer=self.beer, owner=self.me, score=5, comment='моя')
        Rating.objects.create(beer=self.beer, owner=self.other, score=8, comment='чужая')
        self.client.force_login(self.me)

    def test_list_shows_average_of_all_ratings(self):
        response = self.client.get(reverse('beer_list'))

        self.assertEqual(response.status_code, 200)
        # Локаль ru-ru: десятичный разделитель — запятая.
        self.assertContains(response, '6,5/10')
        self.assertContains(response, 'оценок: 2')

    def test_list_shows_own_rating_only(self):
        response = self.client.get(reverse('beer_list'))

        self.assertContains(response, 'Моя оценка: 5/10')
        self.assertNotContains(response, 'Моя оценка: 8/10')

    def test_beer_without_ratings_offers_rating_link(self):
        response = self.client.get(reverse('beer_list'))

        self.assertContains(response, 'Оценок пока нет')
        self.assertContains(
            response, f'{reverse("rating_create")}?beer={self.empty_beer.pk}'
        )

    def test_rating_form_is_prefilled_from_beer_list_link(self):
        response = self.client.get(
            reverse('rating_create'), {'beer': self.empty_beer.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].initial['beer'], str(self.empty_beer.pk))


@override_settings(STORAGES=TEST_STORAGES)
class RatingListVisibilityTests(TestCase):
    """«Оценки» — только свои; счётчик на главной не должен обещать чужие оценки."""

    def setUp(self):
        self.me = User.objects.create_user(username='me', password='pass12345')
        self.other = User.objects.create_user(username='other', password='pass12345')
        self.lonely = User.objects.create_user(username='lonely', password='pass12345')
        self.beer = Beer.objects.create(name='Fruitality')
        Rating.objects.create(beer=self.beer, owner=self.me, score=5)
        Rating.objects.create(beer=self.beer, owner=self.other, score=8)

    def test_rating_list_shows_only_own_ratings(self):
        self.client.force_login(self.me)

        response = self.client.get(reverse('rating_list'))

        self.assertEqual([rating.owner for rating in response.context['ratings']], [self.me])

    def test_rating_list_reports_total_count_of_all_users(self):
        self.client.force_login(self.lonely)

        response = self.client.get(reverse('rating_list'))

        self.assertEqual(list(response.context['ratings']), [])
        self.assertContains(response, 'У вас пока нет оценок')
        self.assertContains(response, 'всего в базе: 2')

    def test_home_counter_counts_only_own_ratings(self):
        self.client.force_login(self.me)

        response = self.client.get(reverse('index'))

        self.assertEqual(response.context['rating_count'], 1)

    def test_home_counter_is_zero_for_user_without_ratings(self):
        self.client.force_login(self.lonely)

        response = self.client.get(reverse('index'))

        self.assertEqual(response.context['rating_count'], 0)

    def test_home_counter_for_anonymous_user_shows_all_ratings(self):
        response = self.client.get(reverse('index'))

        self.assertEqual(response.context['rating_count'], 2)


@override_settings(STORAGES=TEST_STORAGES)
class ReportViewTests(TestCase):
    """Страница «Отчет»: топ хмелей по вкусу и топ производителей по популярности."""

    def setUp(self):
        self.user = User.objects.create_user(username='me', password='pass12345')
        self.citra = Hop.objects.create(name='Citra')
        self.mosaic = Hop.objects.create(name='Mosaic')
        self.unrated_hop = Hop.objects.create(name='Unrated hop')
        self.vendor_a = Vendor.objects.create(name='Пивоварня А')
        self.vendor_b = Vendor.objects.create(name='Пивоварня Б')
        self.vendor_empty = Vendor.objects.create(name='Пустая пивоварня')

        self.beer_one = Beer.objects.create(name='Beer one', vendor=self.vendor_a)
        self.beer_one.hops.set([self.citra])
        self.beer_two = Beer.objects.create(name='Beer two', vendor=self.vendor_a)
        self.beer_two.hops.set([self.citra])
        self.beer_three = Beer.objects.create(name='Beer three', vendor=self.vendor_b)
        self.beer_three.hops.set([self.mosaic])
        # Хмель есть только в пиве без оценок — в отчёт он попасть не должен.
        self.beer_four = Beer.objects.create(name='Beer four')
        self.beer_four.hops.set([self.unrated_hop])

        Rating.objects.create(beer=self.beer_one, owner=self.user, score=10)
        Rating.objects.create(beer=self.beer_two, owner=self.user, score=6)
        Rating.objects.create(beer=self.beer_three, owner=self.user, score=9)

        self.client.force_login(self.user)

    def test_report_link_is_shown_on_home_page(self):
        response = self.client.get(reverse('index'))

        self.assertContains(response, 'href="{}"'.format(reverse('report')))
        self.assertEqual(response.context['report_table_count'], 2)
        self.assertContains(response, '2 отчетов')
        self.assertNotContains(response, 'Топ-5 хмелей и производителей')

    def test_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse('report'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])

    def test_hops_are_ordered_by_average_score_of_their_beers(self):
        response = self.client.get(reverse('report'))

        self.assertEqual(
            [hop.name for hop in response.context['hops']], ['Mosaic', 'Citra']
        )

    def test_hop_row_shows_popularity_and_average_score(self):
        response = self.client.get(reverse('report'))

        citra = next(hop for hop in response.context['hops'] if hop.name == 'Citra')
        self.assertEqual(citra.beers_count, 2)
        self.assertEqual(citra.avg_score, 8)

    def test_hop_without_ratings_is_not_reported(self):
        response = self.client.get(reverse('report'))

        self.assertNotIn(
            'Unrated hop', [hop.name for hop in response.context['hops']]
        )

    def test_hop_links_to_its_best_rated_beer(self):
        response = self.client.get(reverse('report'))

        self.assertContains(response, reverse('beer_detail', args=[self.beer_one.pk]))
        self.assertNotContains(response, reverse('beer_detail', args=[self.beer_two.pk]))

    def test_vendors_are_ordered_by_number_of_beers(self):
        response = self.client.get(reverse('report'))

        vendors = list(response.context['vendors'])
        self.assertEqual([vendor.name for vendor in vendors], ['Пивоварня А', 'Пивоварня Б'])
        self.assertEqual(vendors[0].beers_count, 2)
        self.assertEqual(vendors[0].avg_score, 8)
        self.assertNotIn(self.vendor_empty.name, [vendor.name for vendor in vendors])

    def test_report_shows_only_five_rows(self):
        for index in range(6):
            hop = Hop.objects.create(name=f'Extra hop {index}')
            beer = Beer.objects.create(
                name=f'Extra beer {index}', vendor=self.vendor_b
            )
            beer.hops.set([hop])
            Rating.objects.create(beer=beer, owner=self.user, score=5)

        response = self.client.get(reverse('report'))

        self.assertEqual(len(response.context['hops']), 5)
        self.assertEqual(len(response.context['vendors']), 2)

    def test_report_is_linked_from_menu_and_home_page(self):
        report_url = reverse('report')

        home = self.client.get(reverse('index'))
        # Карточка на главной и пункт в меню.
        self.assertContains(home, 'href="{}"'.format(report_url), count=2)

        beer_list = self.client.get(reverse('beer_list'))
        self.assertContains(beer_list, 'href="{}"'.format(report_url), count=1)

    def test_empty_report_renders_hints(self):
        Beer.objects.all().delete()

        response = self.client.get(reverse('report'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Пока нет оценённого пива с хмелем.')
        self.assertContains(response, 'Пока нет пива с указанным производителем.')


@override_settings(STORAGES=TEST_STORAGES)
class AccessMatrixTests(TestCase):
    """Права каталога и оценок проверяются сервером для каждой роли."""

    def setUp(self):
        self.user = User.objects.create_user(username='reader', password='pass12345')
        self.staff = User.objects.create_user(
            username='catalog-admin', password='pass12345', is_staff=True
        )
        self.other = User.objects.create_user(username='another', password='pass12345')
        self.vendor = Vendor.objects.create(name='Пивоварня')
        self.hop = Hop.objects.create(name='Citra')
        self.beer = Beer.objects.create(name='IPA', vendor=self.vendor)
        self.empty_beer = Beer.objects.create(name='Lager')
        self.own_rating = Rating.objects.create(
            beer=self.beer, owner=self.user, score=5, comment='моя оценка'
        )
        self.foreign_rating = Rating.objects.create(
            beer=self.beer, owner=self.other, score=8, comment='чужая оценка'
        )
        self.ownerless_rating = Rating.objects.create(
            beer=self.beer, owner=None, score=4
        )

    def test_guest_is_redirected_to_login(self):
        protected_urls = (
            reverse('beer_list'),
            reverse('hop_list'),
            reverse('vendor_list'),
            reverse('rating_list'),
            reverse('report'),
        )
        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse('login'), response['Location'])
                self.assertIn('next=', response['Location'])

    def test_guest_gets_login_redirect_for_rating_edit(self):
        response = self.client.get(
            reverse('rating_update', args=[self.foreign_rating.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])
        self.assertIn('next=', response['Location'])

    def test_beer_list_hides_catalog_actions_for_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('beer_list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Добавить пиво')
        self.assertNotContains(response, reverse('beer_update', args=[self.beer.pk]))
        self.assertNotContains(response, reverse('beer_delete', args=[self.beer.pk]))
        self.assertContains(response, 'Оценить')
        self.assertContains(response, 'Изменить оценку')

    def test_beer_detail_hides_catalog_actions_for_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('beer_detail', args=[self.beer.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('beer_update', args=[self.beer.pk]))
        self.assertNotContains(response, reverse('beer_delete', args=[self.beer.pk]))

    def test_user_cannot_open_beer_edit(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('beer_update', args=[self.beer.pk]))

        self.assertEqual(response.status_code, 403)

    def test_user_cannot_delete_beer(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('beer_delete', args=[self.beer.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Beer.objects.filter(pk=self.beer.pk).exists())

    def test_user_cannot_change_beer(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('beer_update', args=[self.beer.pk]),
            {'name': 'Изменённое пиво'},
        )

        self.assertEqual(response.status_code, 403)
        self.beer.refresh_from_db()
        self.assertEqual(self.beer.name, 'IPA')

    def test_user_cannot_create_hop(self):
        self.client.force_login(self.user)
        original_count = Hop.objects.count()

        response = self.client.post(reverse('hop_create'), {'name': 'New hop'})

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Hop.objects.count(), original_count)

    def test_user_cannot_create_other_catalog_items(self):
        self.client.force_login(self.user)

        cases = (
            ('vendor_create', {'name': 'New vendor'}, Vendor),
            ('beer_create', {'name': 'New beer'}, Beer),
        )
        for url_name, data, model in cases:
            with self.subTest(url_name=url_name):
                original_count = model.objects.count()
                response = self.client.post(reverse(url_name), data)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(model.objects.count(), original_count)

    def test_user_cannot_edit_or_delete_vendor(self):
        self.client.force_login(self.user)

        edit_response = self.client.get(
            reverse('vendor_update', args=[self.vendor.pk])
        )
        delete_response = self.client.post(
            reverse('vendor_delete', args=[self.vendor.pk])
        )

        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertTrue(Vendor.objects.filter(pk=self.vendor.pk).exists())
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.name, 'Пивоварня')

    def test_user_cannot_edit_or_delete_hop(self):
        self.client.force_login(self.user)

        edit_response = self.client.post(
            reverse('hop_update', args=[self.hop.pk]), {'name': 'Changed hop'}
        )
        delete_response = self.client.post(
            reverse('hop_delete', args=[self.hop.pk])
        )

        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.assertTrue(Hop.objects.filter(pk=self.hop.pk).exists())
        self.hop.refresh_from_db()
        self.assertEqual(self.hop.name, 'Citra')

    def test_staff_sees_catalog_actions(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('beer_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Добавить пиво')
        self.assertContains(response, reverse('beer_update', args=[self.beer.pk]))
        self.assertContains(response, reverse('beer_delete', args=[self.beer.pk]))

        detail_response = self.client.get(
            reverse('beer_detail', args=[self.beer.pk])
        )
        self.assertContains(
            detail_response, reverse('beer_update', args=[self.beer.pk])
        )
        self.assertContains(
            detail_response, reverse('beer_delete', args=[self.beer.pk])
        )

    def test_staff_can_delete_beer(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('beer_delete', args=[self.beer.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('beer_list'))
        self.assertFalse(Beer.objects.filter(pk=self.beer.pk).exists())

    def test_user_creates_rating_owned_by_current_user(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('rating_create'),
            {'beer': self.empty_beer.pk, 'score': 7, 'comment': 'Новая'},
        )

        self.assertEqual(response.status_code, 302)
        rating = Rating.objects.get(beer=self.empty_beer)
        self.assertEqual(rating.owner, self.user)

    def test_user_cannot_open_foreign_rating_edit(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('rating_update', args=[self.foreign_rating.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_foreign_rating(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('rating_delete', args=[self.foreign_rating.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Rating.objects.filter(pk=self.foreign_rating.pk).exists())

    def test_owner_can_update_own_rating(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('rating_update', args=[self.own_rating.pk]),
            {'beer': self.beer.pk, 'score': 9, 'comment': 'обновлённая оценка'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('rating_list'))
        self.own_rating.refresh_from_db()
        self.assertEqual(self.own_rating.score, 9)
        self.assertEqual(self.own_rating.comment, 'обновлённая оценка')

    def test_staff_cannot_edit_or_delete_foreign_rating_via_web(self):
        self.client.force_login(self.staff)

        edit_response = self.client.get(
            reverse('rating_update', args=[self.foreign_rating.pk])
        )
        delete_response = self.client.post(
            reverse('rating_delete', args=[self.foreign_rating.pk])
        )

        self.assertEqual(edit_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        self.assertTrue(Rating.objects.filter(pk=self.foreign_rating.pk).exists())

    def test_ownerless_rating_is_unavailable_via_web(self):
        for user in (self.user, self.staff):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(
                    reverse('rating_update', args=[self.ownerless_rating.pk])
                )
                self.assertEqual(response.status_code, 404)

    def test_permission_denied_page_is_russian(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('beer_update', args=[self.beer.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Недостаточно прав', status_code=403)
        self.assertContains(
            response,
            'Изменять каталог может только администратор.',
            status_code=403,
        )
        self.assertContains(
            response,
            f'href="{reverse("index")}"',
            status_code=403,
        )

    def test_permission_denied_is_logged(self):
        self.client.force_login(self.user)

        with self.assertLogs('brewery', level='WARNING') as captured:
            response = self.client.post(reverse('hop_create'), {'name': 'Private'})

        self.assertEqual(response.status_code, 403)
        self.assertTrue(any('reader' in line for line in captured.output))
        self.assertTrue(any(reverse('hop_create') in line for line in captured.output))

        with self.assertLogs('brewery', level='WARNING') as foreign_logs:
            foreign_response = self.client.get(
                reverse('rating_update', args=[self.foreign_rating.pk])
            )

        self.assertEqual(foreign_response.status_code, 404)
        self.assertTrue(any('reader' in line for line in foreign_logs.output))
        self.assertTrue(
            any(
                reverse('rating_update', args=[self.foreign_rating.pk]) in line
                for line in foreign_logs.output
            )
        )

    def test_lists_hide_catalog_actions_for_user(self):
        self.client.force_login(self.user)

        for url_name, create_name, update_name, delete_name, object_pk in (
            ('hop_list', 'hop_create', 'hop_update', 'hop_delete', self.hop.pk),
            (
                'vendor_list',
                'vendor_create',
                'vendor_update',
                'vendor_delete',
                self.vendor.pk,
            ),
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, reverse(create_name))
                self.assertNotContains(response, reverse(update_name, args=[object_pk]))
                self.assertNotContains(response, reverse(delete_name, args=[object_pk]))

    def test_rating_list_shows_actions_only_for_own_ratings(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('rating_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, reverse('rating_update', args=[self.own_rating.pk])
        )
        self.assertContains(
            response, reverse('rating_delete', args=[self.own_rating.pk])
        )
        self.assertNotContains(
            response, reverse('rating_update', args=[self.foreign_rating.pk])
        )

    def test_user_cannot_reach_admin(self):
        self.client.force_login(self.user)

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])
        for url_name in ('beer_list', 'hop_list', 'vendor_list', 'rating_list'):
            page = self.client.get(reverse(url_name))
            self.assertNotContains(page, 'name="is_staff"')


# ---------- SPEC-002: вход через Yandex ID ----------

# Ключи провайдера подставляются в тестах; реальные значения — в окружении.
YANDEX_CREDENTIALS = {
    'YANDEX_OAUTH_ENABLED': True,
    'SOCIALACCOUNT_PROVIDERS': {
        'yandex': {
            'APP': {'client_id': 'test-client-id', 'secret': 'test-secret'},
            'SCOPE': ['login:email', 'login:info'],
        },
    },
}

# Профиль, который якобы вернул Yandex.
YANDEX_PROFILE = {
    'id': '4611686018427387904',
    'default_email': 'new@example.com',
    'display_name': 'Иван',
    'first_name': 'Иван',
    'last_name': 'Петров',
    'emails': ['new@example.com'],
}


class FakeYandexResponse:
    """Ответ HTTP-сессии allauth без сети."""

    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.text = ''

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'Yandex вернул {self.status_code}')

    def json(self):
        return self._data


class FakeYandexSession:
    """Подмена сессии requests: тесты не ходят в сеть."""

    def __init__(self, data=None, error=None):
        self._data = data
        self._error = error

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def get(self, *args, **kwargs):
        if self._error is not None:
            raise self._error
        return FakeYandexResponse(self._data)


class YandexOAuthHelpers:
    """Шаги соцвхода, общие для тестов: старт OAuth и ответ Yandex."""

    def start_yandex_login(self, **params):
        response = self.client.get(reverse('yandex_login'), params)
        self.assertEqual(response.status_code, 302)
        location = response['Location']
        state = parse_qs(urlparse(location).query).get('state', [''])[0]
        self.assertTrue(state, 'Yandex должен получить параметр state')
        return location, state

    def yandex_callback(
        self, profile=None, state=None, code='test-code', error=None, session_error=None
    ):
        params = {'state': state}
        if error:
            params['error'] = error
            return self.client.get(reverse('yandex_callback'), params)
        params['code'] = code
        with patch.object(
            HopBeerSocialAccountAdapter,
            'get_requests_session',
            return_value=FakeYandexSession(profile, session_error),
        ), patch.object(
            YandexOAuth2Adapter,
            'get_access_token_data',
            return_value={'access_token': 'test-token'},
        ):
            return self.client.get(reverse('yandex_callback'), params)

    def login_page_after(self, response):
        """Перейти по редиректу и вернуть страницу, на которой видно сообщение."""
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response['Location'])
        self.assertEqual(page.status_code, 200)
        return page


@override_settings(STORAGES=TEST_STORAGES, **YANDEX_CREDENTIALS)
class YandexLoginTests(YandexOAuthHelpers, TestCase):
    """Вход через Yandex ID, самозапись и отказы (SPEC-002)."""

    def setUp(self):
        self.beer = Beer.objects.create(name='Fruitality', style='Fruited Milk IPA')

    def create_social_user(self, profile=None):
        _, state = self.start_yandex_login()
        response = self.yandex_callback(profile=profile or YANDEX_PROFILE, state=state)
        self.assertEqual(response.status_code, 302)
        return User.objects.get(email=YANDEX_PROFILE['default_email'])

    def test_guest_still_gets_login_redirect_with_next(self):
        response = self.client.get(reverse('beer_list'))

        self.assertEqual(response.status_code, 302)
        location = urlparse(response['Location'])
        self.assertEqual(location.path, '/accounts/login/')
        self.assertEqual(parse_qs(location.query)['next'], [reverse('beer_list')])
        self.assertEqual(self.client.get(response['Location']).status_code, 200)

    def test_login_page_shows_yandex_button_and_password_form(self):
        response = self.client.get(reverse('account_login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Войти через Yandex ID')
        self.assertContains(response, 'name="login"')
        self.assertContains(response, 'name="password"')

    def test_yandex_button_redirects_to_provider_with_state(self):
        location, state = self.start_yandex_login(next=reverse('beer_list'))

        provider_url = urlparse(location)
        self.assertEqual(
            f'{provider_url.scheme}://{provider_url.netloc}{provider_url.path}',
            'https://oauth.yandex.com/authorize',
        )
        params = parse_qs(provider_url.query)
        self.assertEqual(params['client_id'], ['test-client-id'])
        self.assertEqual(
            params['redirect_uri'], ['http://testserver/accounts/yandex/login/callback/']
        )
        self.assertEqual(params['state'], [state])

    def test_first_yandex_login_creates_user_and_logs_in(self):
        _, state = self.start_yandex_login(next=reverse('beer_list'))

        response = self.yandex_callback(profile=YANDEX_PROFILE, state=state)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('beer_list'))
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(email='new@example.com')
        self.assertFalse(user.is_staff)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertEqual(SocialAccount.objects.filter(user=user).count(), 1)

    def test_social_user_has_no_usable_password(self):
        user = self.create_social_user()

        self.assertFalse(user.has_usable_password())
        self.client.logout()
        response = self.client.post(
            reverse('account_login'),
            {'login': user.get_username(), 'password': 'pass12345'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_new_social_user_cannot_change_catalog(self):
        self.create_social_user()
        hop_count = Hop.objects.count()
        beer_count = Beer.objects.count()

        beer_response = self.client.post(reverse('beer_create'), {'name': 'Новое пиво'})
        hop_response = self.client.post(reverse('hop_create'), {'name': 'Новый хмель'})

        self.assertEqual(beer_response.status_code, 403)
        self.assertEqual(hop_response.status_code, 403)
        self.assertEqual(Beer.objects.count(), beer_count)
        self.assertEqual(Hop.objects.count(), hop_count)

    def test_second_yandex_login_uses_same_account(self):
        user = self.create_social_user()
        self.client.logout()

        _, state = self.start_yandex_login()
        self.yandex_callback(profile=YANDEX_PROFILE, state=state)

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertEqual(SocialAccount.objects.count(), 1)

    def test_existing_email_is_not_linked_automatically(self):
        old_user = User.objects.create_user(
            username='old', password='pass12345', email='old@example.com'
        )
        profile = dict(
            YANDEX_PROFILE, default_email='old@example.com', emails=['old@example.com']
        )
        _, state = self.start_yandex_login()

        response = self.yandex_callback(profile=profile, state=state)

        page = self.login_page_after(response)
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(SocialAccount.objects.exists())
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(page, 'Аккаунт с таким email уже существует')
        self.assertTrue(User.objects.filter(pk=old_user.pk).exists())

    def test_provider_cancel_keeps_guest_on_login_page(self):
        _, state = self.start_yandex_login()

        response = self.yandex_callback(state=state, error='access_denied')

        page = self.login_page_after(response)
        self.assertContains(page, 'Вход через Yandex ID отменён или не удался')
        self.assertContains(page, 'name="password"')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_provider_error_shows_message_not_500(self):
        _, state = self.start_yandex_login()

        response = self.yandex_callback(
            profile=YANDEX_PROFILE,
            state=state,
            session_error=requests.ConnectionError('Yandex недоступен'),
        )

        page = self.login_page_after(response)
        self.assertContains(page, 'Вход через Yandex ID отменён или не удался')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(User.objects.count(), 0)

    def test_missing_email_does_not_create_account(self):
        profile = {'id': '42', 'display_name': 'Без почты'}
        _, state = self.start_yandex_login()

        response = self.yandex_callback(profile=profile, state=state)

        page = self.login_page_after(response)
        self.assertEqual(User.objects.count(), 0)
        self.assertFalse(SocialAccount.objects.exists())
        self.assertContains(page, 'Yandex не передал адрес электронной почты')

    @override_settings(YANDEX_OAUTH_ENABLED=False, SOCIALACCOUNT_PROVIDERS={})
    def test_yandex_button_hidden_without_credentials(self):
        response = self.client.get(reverse('account_login'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Войти через Yandex ID')
        self.assertContains(response, 'name="password"')
        user = User.objects.create_user(username='local', password='pass12345')
        login_response = self.client.post(
            reverse('account_login'), {'login': 'local', 'password': 'pass12345'}
        )
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        start_response = self.client.get(reverse('yandex_login'))
        self.assertEqual(start_response.status_code, 302)
        self.assertEqual(start_response['Location'], reverse('account_login'))

    def test_existing_user_keeps_password_login_after_migrations(self):
        user = User.objects.create_user(
            username='keeper',
            password='pass12345',
            email='keeper@example.com',
            is_staff=True,
        )
        rating = Rating.objects.create(beer=self.beer, owner=user, score=7)

        response = self.client.post(
            reverse('account_login'), {'login': 'keeper', 'password': 'pass12345'}
        )

        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.check_password('pass12345'))
        self.assertEqual(Rating.objects.get(pk=rating.pk).owner_id, user.pk)

    def test_username_collision_creates_unique_username(self):
        existing = User.objects.create_user(
            username='Иван', password='pass12345', email='other@example.com'
        )
        _, state = self.start_yandex_login()

        self.yandex_callback(profile=YANDEX_PROFILE, state=state)

        self.assertEqual(User.objects.count(), 2)
        new_user = User.objects.get(email='new@example.com')
        self.assertNotEqual(new_user.get_username(), existing.get_username())
        existing.refresh_from_db()
        self.assertEqual(existing.get_username(), 'Иван')
        self.assertEqual(existing.email, 'other@example.com')

    def test_social_user_can_log_out_with_post(self):
        self.create_social_user()

        response = self.client.post(reverse('account_logout'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('index'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('beer_list')).status_code, 302)


@override_settings(STORAGES=TEST_STORAGES, **YANDEX_CREDENTIALS)
class SocialAccountConnectionsTests(YandexOAuthHelpers, TestCase):
    """Страница связей: привязка и отвязка Yandex (SPEC-002 FR-007…FR-009)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='reader', password='pass12345', email='reader@example.com'
        )

    def connect_yandex(self, profile=None):
        self.client.force_login(self.user)
        _, state = self.start_yandex_login(process='connect')
        return self.yandex_callback(profile=profile or YANDEX_PROFILE, state=state)

    def test_guest_gets_login_redirect_for_connections_page(self):
        response = self.client.get(reverse('socialaccount_connections'))

        self.assertEqual(response.status_code, 302)
        location = urlparse(response['Location'])
        self.assertEqual(location.path, '/accounts/login/')
        self.assertEqual(
            parse_qs(location.query)['next'], [reverse('socialaccount_connections')]
        )

    def test_authenticated_user_connects_yandex_and_signs_in_with_it(self):
        response = self.connect_yandex()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('socialaccount_connections'))
        account = SocialAccount.objects.get(user=self.user, provider='yandex')
        self.assertEqual(account.uid, YANDEX_PROFILE['id'])
        page = self.client.get(reverse('socialaccount_connections'))
        self.assertContains(page, 'Yandex')
        self.assertContains(page, 'Отключить')
        self.client.logout()

        _, state = self.start_yandex_login()
        self.yandex_callback(profile=YANDEX_PROFILE, state=state)

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_user_with_password_can_disconnect_yandex(self):
        self.connect_yandex()
        account = SocialAccount.objects.get(user=self.user)

        response = self.client.post(
            reverse('socialaccount_connections'), {'account': account.pk}
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(SocialAccount.objects.exists())
        page = self.client.get(reverse('socialaccount_connections'))
        self.assertContains(page, 'Yandex ID отключён')
        self.client.logout()
        login_response = self.client.post(
            reverse('account_login'), {'login': 'reader', 'password': 'pass12345'}
        )
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)
        self.client.logout()

        _, state = self.start_yandex_login()
        self.yandex_callback(profile=YANDEX_PROFILE, state=state)

        self.assertNotEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_user_without_password_cannot_disconnect_yandex(self):
        social_user = User.objects.create_user(username='social', password=None)
        account = SocialAccount.objects.create(
            user=social_user,
            provider='yandex',
            uid=YANDEX_PROFILE['id'],
            extra_data={'default_email': 'social@example.com'},
        )
        self.client.force_login(social_user)

        response = self.client.post(
            reverse('socialaccount_connections'), {'account': account.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Сначала задайте пароль — иначе вы не сможете войти.')
        self.assertTrue(SocialAccount.objects.filter(pk=account.pk).exists())

    def test_connections_page_hints_empty_state(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('socialaccount_connections'))

        self.assertContains(response, 'Пока нет подключённых аккаунтов.')
        self.assertContains(response, 'Подключить Yandex ID')


@override_settings(STORAGES=TEST_STORAGES, **YANDEX_CREDENTIALS)
class SocialLoginLoggingTests(YandexOAuthHelpers, TestCase):
    """Соцвход пишется в логгер brewery без секретов (SPEC-002 FR-014)."""

    def test_social_login_failure_is_logged_without_secrets(self):
        _, state = self.start_yandex_login()

        with self.assertLogs('brewery', 'WARNING') as logs:
            self.yandex_callback(state=state, error='access_denied')

        output = '\n'.join(logs.output)
        self.assertIn('yandex', output)
        self.assertIn('cancelled', output)
        self.assertNotIn('test-token', output)
        self.assertNotIn('test-secret', output)
        self.assertNotIn('test-code', output)

    def test_social_login_success_is_logged(self):
        _, state = self.start_yandex_login()

        with self.assertLogs('brewery', 'INFO') as logs:
            self.yandex_callback(profile=YANDEX_PROFILE, state=state)

        output = '\n'.join(logs.output)
        user = User.objects.get(email='new@example.com')
        self.assertIn('yandex', output)
        self.assertIn(user.get_username(), output)
        self.assertNotIn('test-token', output)
        self.assertNotIn('test-secret', output)


@override_settings(STORAGES=TEST_STORAGES)
class PrivacyPolicyTests(TestCase):
    """Публичная политика конфиденциальности (SPEC-002 FR-013)."""

    def test_privacy_page_is_public_and_describes_data(self):
        response = self.client.get(reverse('privacy'))

        self.assertEqual(response.status_code, 200)
        for heading in (
            'Какие данные мы получаем',
            'Зачем они нужны',
            'Где они хранятся',
            'Чего мы не получаем',
            'Как удалить учётную запись',
            'Контакты',
        ):
            self.assertContains(response, heading)
        self.assertContains(self.client.get(reverse('account_login')), 'Политика конфиденциальности')
        user = User.objects.create_user(username='reader', password='pass12345')
        self.client.force_login(user)
        self.assertContains(
            self.client.get(reverse('socialaccount_connections')),
            'Политика конфиденциальности',
        )
