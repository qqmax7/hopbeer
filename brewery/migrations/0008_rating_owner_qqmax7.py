"""Проставляем владельца существующим оценкам.

Все оценки, созданные до появления поля `owner`, принадлежат пользователю
`qqmax7`. Если такого пользователя нет — миграция ничего не меняет.
"""
from django.conf import settings
from django.db import migrations

OWNER_USERNAME = 'qqmax7'


def set_owner_to_qqmax7(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Rating = apps.get_model('brewery', 'Rating')

    owner = User.objects.filter(username=OWNER_USERNAME).first()
    if owner is None:
        return

    Rating.objects.filter(owner__isnull=True).update(owner=owner)


def clear_owner(apps, schema_editor):
    Rating = apps.get_model('brewery', 'Rating')
    Rating.objects.update(owner=None)


class Migration(migrations.Migration):

    dependencies = [
        ('brewery', '0007_rating_owner'),
    ]

    operations = [
        migrations.RunPython(set_owner_to_qqmax7, clear_owner),
    ]
