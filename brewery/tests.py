"""Тесты списка пива и отображения оценок."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

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
