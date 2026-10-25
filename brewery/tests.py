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
