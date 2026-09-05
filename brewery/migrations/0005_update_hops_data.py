"""Data-миграция: страны и годы создания сортов хмеля."""
from django.db import migrations

HOPS = [
    # (name, country, year)
    ('Cascade', 'США', 1956),
    ('Citra', 'США', 2007),
    ('Mosaic', 'США', 2012),
    ('Centennial', 'США', 1990),
    ('Chinook', 'США', 1985),
    ('Amarillo', 'США', 2009),
    ('Simcoe', 'США', 2000),
    ('Galaxy (AU)', 'Австралия', 2009),
    ('Saaz', 'Чехия', 1900),
    ('Hallertau Mittelfrüh', 'Германия', 1900),
    ('Tettnanger', 'Германия', 1900),
    ('Spalt', 'Германия', 1900),
    ('Nelson Sauvin (NZ)', 'Новая Зеландия', 2000),
    ('Motueka (NZ)', 'Новая Зеландия', 2005),
    ('Rakau (NZ)', 'Новая Зеландия', 2005),
    ('Willamette', 'США', 1976),
    ('Fuggles', 'Великобритания', 1875),
    ('Goldings (East Kent)', 'Великобритания', 1790),
    ('Perle', 'Германия', 1978),
    ('Hersbrucker', 'Германия', 1900),
    ('Liberty', 'США', 1983),
    ('Crystal', 'США', 1983),
    ('Mt. Hood', 'США', 1989),
    ('Nugget', 'США', 1982),
    ('Columbus/Tomahawk', 'США', 1991),
    ('Warrior', 'США', 2000),
    ('Bravo', 'США', 2006),
    ('Magnum', 'Германия', 1980),
    ('Northern Brewer', 'Великобритания', 1934),
    ('Styrian Goldings', 'Словения', 1950),
    ('Sorachi Ace (JP)', 'Япония', 1980),
    ('Southern Star (NZ)', 'Новая Зеландия', 2003),
    ('Pacifica (NZ)', 'Новая Зеландия', 1994),
    ('Green Bullet (NZ)', 'Новая Зеландия', 1972),
    ('Super Alpha (NZ)', 'Новая Зеландия', 1976),
    ('Topaz (AU)', 'Австралия', 2008),
    ('Vic Secret (AU)', 'Австралия', 2013),
    ('Ella (AU)', 'Австралия', 1998),
    ('Enigma (AU)', 'Австралия', 2010),
    ('Mandarina Bavaria', 'Германия', 2012),
    ('Huell Melon', 'Германия', 2012),
    ('Azacca', 'США', 2012),
    ('El Dorado', 'США', 2012),
    ('Cashmere', 'США', 2013),
    ('Idaho 7', 'США', 2015),
    ('Sabro', 'США', 2018),
    ('Strata', 'США', 2018),
    ('Lunar', 'США', 2016),
    ('Ahtanum', 'США', 1998),
    ('Polaris', 'Германия', 2012),
]


def forwards(apps, schema_editor):
    Hop = apps.get_model('brewery', 'Hop')
    for name, country, year in HOPS:
        Hop.objects.filter(name=name).update(country=country, year=year)


def backwards(apps, schema_editor):
    Hop = apps.get_model('brewery', 'Hop')
    Hop.objects.filter(name__in=[h[0] for h in HOPS]).update(country='', year=None)


class Migration(migrations.Migration):

    dependencies = [
        ('brewery', '0004_beer_gost_beer_og_beer_value_deal_hop_country_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]