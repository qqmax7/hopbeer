#!/usr/bin/env python3
"""Одноразовый импорт пива с дегустации 12.09.2026.

Фотографии этикеток должны лежать в media/beers/ (имена как в PHOTOS).
Запуск на сервере:
    cd /opt/hopbeer && set -a && . ./.env && set +a && ./venv/bin/python scripts/import_beers_2026_09.py
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beer_app.settings')

import django

django.setup()

from django.core.files import File

from brewery.models import Beer, Hop, Vendor

PHOTOS_DIR = os.path.join(BASE_DIR, 'media', 'beers')

VENDORS = {
    'chibis': {'name': 'Chibis Brewery', 'country': 'Россия'},
    'ability': {'name': 'Ability / Saliwa', 'country': 'Россия'},
    'stamm': {'name': 'Stamm Brewing', 'country': 'Россия'},
    'bigvillage': {'name': 'Big Village Brewery', 'country': 'Россия', 'city': 'Краснодар'},
    'plague': {'name': 'Plague Brew', 'country': 'Россия', 'city': 'Санкт-Петербург'},
    'zagovor': {'name': 'Zagovor Brewery', 'country': 'Россия', 'city': 'Москва'},
    'mitra': {'name': 'Mitra', 'country': 'Россия', 'city': 'Волгоград'},
    'rewort': {'name': 'Rewort', 'country': 'Россия'},
}

BEERS = [
    {
        'name': 'Гиперпинк',
        'style': 'New England IPA',
        'abv': '6.00',
        'og': 16,
        'vendor': None,
        'hops': ['Riwaka', 'Krush Cryo', 'Citra'],
        'file': 'photo_2026-09-12_22-15-26.jpg',
        'description': 'New England IPA с хмелями Riwaka, Krush Cryo и Citra. ЭНС 16.0%, алк. 6.0%.',
    },
    {
        'name': 'Коллаж',
        'style': 'New England IPA',
        'abv': '6.20',
        'og': 17,
        'vendor': 'chibis',
        'hops': ['Citra', 'Riwaka', 'Moutere', 'Nelson Sauvin', 'Citra Cryo'],
        'file': 'photo_2026-09-12_22-15-36.jpg',
        'description': 'New England IPA с хмелями Citra, Riwaka, Moutere, Nelson Sauvin и Citra Cryo. Алк. 6.2%, ЭНС 16.7%.',
    },
    {
        'name': 'Living Water',
        'style': 'Session NEIPA',
        'abv': '4.50',
        'og': None,
        'vendor': 'ability',
        'hops': ['Krush Cryo', 'Riwaka', 'Amplifire'],
        'file': 'photo_2026-09-12_22-15-43.jpg',
        'description': 'Session New England IPA с хмелями Krush, Riwaka и Amplifire. Алк. 4.5%.',
    },
    {
        'name': 'Turbid Flow',
        'style': 'New England IPA',
        'abv': '7.00',
        'og': 17,
        'vendor': 'stamm',
        'hops': [],
        'file': 'photo_2026-09-12_22-15-48.jpg',
        'description': 'New England IPA. Плотность 17%, алк. 7%.',
    },
    {
        'name': 'Воспоминание',
        'style': 'DDH NEIPA',
        'abv': None,
        'og': None,
        'vendor': 'bigvillage',
        'hops': [],
        'file': 'photo_2026-09-12_22-15-53.jpg',
        'description': 'Double dry-hopped New England IPA.',
    },
    {
        'name': 'Replica Nelson Sauvin',
        'style': 'DDH NEIPA',
        'abv': '6.50',
        'ibu': 25,
        'og': 16,
        'vendor': 'zagovor',
        'hops': ['Nelson Sauvin'],
        'file': 'photo_2026-09-12_22-15-58.jpg',
        'description': 'DDH New England IPA с хмелем Nelson Sauvin. Плотность 16%, алк. 6.5%, IBU 25.',
    },
    {
        'name': 'Separator',
        'style': 'Doppelbock',
        'abv': '7.00',
        'og': None,
        'vendor': 'plague',
        'hops': [],
        'file': 'photo_2026-09-12_22-16-07.jpg',
        'description': 'Доппельбок. Алк. 7.0%, объём 330 мл.',
    },
    {
        'name': 'Village Bock',
        'style': 'Weizen-Doppelbock',
        'abv': None,
        'og': None,
        'vendor': 'bigvillage',
        'hops': [],
        'file': 'photo_2026-09-12_22-16-12.jpg',
        'description': 'Пшеничный доппельбок.',
    },
    {
        'name': 'Летний Соблазн',
        'style': 'New England IPA',
        'abv': '6.10',
        'og': 16,
        'vendor': 'chibis',
        'hops': ['Citra Cryo', 'Simcoe Cryo', 'Vic Secret'],
        'file': 'photo_2026-09-12_22-16-16.jpg',
        'description': 'New England IPA с хмелями Citra Cryo, Simcoe Cryo и Vic Secret. Алк. 6.1%, ЭНС 16.1%.',
    },
    {
        'name': 'Сочняк',
        'style': 'New England IPA',
        'abv': '6.00',
        'og': 16,
        'vendor': 'chibis',
        'hops': ['Simcoe Cryo', 'Enigma', 'Citra'],
        'file': 'photo_2026-09-12_22-16-21.jpg',
        'description': 'New England IPA с хмелями Simcoe Cryo, Enigma и Citra. Алк. 6.0%, ЭНС 16.0%.',
    },
    {
        'name': 'Весна',
        'style': 'New England IPA',
        'abv': '6.20',
        'og': 16,
        'vendor': 'chibis',
        'hops': ['Rakau Amplifire', 'Nectaron', 'El Dorado', 'Citra'],
        'file': 'photo_2026-09-12_22-16-25.jpg',
        'description': 'New England IPA с хмелями Rakau Amplifire, Nectaron, El Dorado и Citra. Алк. 6.2%, ЭНС 16.2%.',
    },
    {
        'name': 'India Pale Ale',
        'style': 'India Pale Ale',
        'abv': '6.30',
        'ibu': 44,
        'og': 14,
        'vendor': 'mitra',
        'hops': ['Styrian Wolf', 'Tango'],
        'file': 'photo_2026-09-12_22-16-30.jpg',
        'description': 'India Pale Ale с хмелями Styrian Wolf и Tango. Алк. 6.3%, IBU 44, ЭНС 13.8%.',
    },
    {
        'name': 'Миниатюра',
        'style': 'Микро НЕИПА',
        'abv': None,
        'og': None,
        'vendor': 'rewort',
        'hops': ['Citra', 'Mosaic', 'Nelson Sauvin'],
        'file': 'photo_2026-09-12_22-16-34.jpg',
        'description': 'Микро НЕИПА с хмелями Цитра, Мозаик и Нельсон Совин.',
    },
    {
        'name': 'Хорошо',
        'style': 'New England IPA',
        'abv': '6.00',
        'og': 16,
        'vendor': 'chibis',
        'hops': ['Elani', 'Superdelic', 'Citra'],
        'file': 'photo_2026-09-12_22-16-38.jpg',
        'description': 'New England IPA с хмелями Elani, Superdelic и Citra. Алк. 6.0%, ЭНС 16.0%.',
    },
    {
        'name': 'Fruitality',
        'style': 'Fruited Milk IPA',
        'abv': '6.80',
        'og': None,
        'vendor': None,
        'hops': [],
        'file': 'photo_2026-09-12_22-16-43.jpg',
        'description': 'Фруктовый milk IPA. Алк. 6.8%.',
    },
    {
        'name': 'Old Song',
        'style': 'DDH NEIPA',
        'abv': None,
        'og': None,
        'vendor': 'bigvillage',
        'hops': [],
        'file': 'photo_2026-09-12_22-16-48.jpg',
        'description': 'Double dry-hopped New England IPA.',
    },
]


def main():
    vendors = {}
    for key, data in VENDORS.items():
        vendors[key], created = Vendor.objects.get_or_create(
            name=data['name'],
            defaults={
                'country': data.get('country', ''),
                'city': data.get('city', ''),
            },
        )
        print('vendor', 'created' if created else 'exists ', data['name'])

    hops = {}
    for item in BEERS:
        for hop_name in item['hops']:
            if hop_name not in hops:
                hops[hop_name], _ = Hop.objects.get_or_create(name=hop_name)
    print('hops total:', len(hops))

    created_count = 0
    for item in BEERS:
        if Beer.objects.filter(name=item['name']).exists():
            print('skip (already exists):', item['name'])
            continue
        beer = Beer(
            name=item['name'],
            style=item['style'],
            abv=item.get('abv'),
            ibu=item.get('ibu'),
            og=item.get('og'),
            description=item['description'],
            vendor=vendors.get(item['vendor']) if item['vendor'] else None,
        )
        photo_path = os.path.join(PHOTOS_DIR, item['file'])
        with open(photo_path, 'rb') as fh:
            beer.image.save(item['file'], File(fh), save=False)
        beer.save()
        for hop_name in item['hops']:
            beer.hops.add(hops[hop_name])
        created_count += 1
        print('created:', beer.name, '| image:', beer.image.name)

    print('done, created beers:', created_count)


if __name__ == '__main__':
    main()
