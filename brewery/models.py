"""Модели приложения brewery.

Схема адаптирована из обсуждения (Supabase) под локальную SQLite-базу.
"""
from django.db import models


class Vendor(models.Model):
    """Производитель (пивоварня)."""

    name = models.CharField('Название', max_length=200)
    country = models.CharField('Страна', max_length=100, blank=True)
    website = models.URLField('Сайт', blank=True)

    class Meta:
        verbose_name = 'Производитель'
        verbose_name_plural = 'Производители'
        ordering = ['name']

    def __str__(self):
        return self.name


class Hop(models.Model):
    """Сорт хмеля."""

    name = models.CharField('Название', max_length=200)
    alpha_acid = models.DecimalField(
        'Альфа-кислота, %', max_digits=4, decimal_places=2, null=True, blank=True
    )
    aroma = models.TextField('Аромат', blank=True)

    class Meta:
        verbose_name = 'Хмель'
        verbose_name_plural = 'Хмель'
        ordering = ['name']

    def __str__(self):
        return self.name


class Beer(models.Model):
    """Пиво."""

    name = models.CharField('Название', max_length=200)
    style = models.CharField('Стиль', max_length=200, blank=True)
    abv = models.DecimalField(
        'Крепость, %', max_digits=4, decimal_places=2, null=True, blank=True
    )
    ibu = models.PositiveIntegerField('IBU', null=True, blank=True)
    description = models.TextField('Описание', blank=True)
    vendor = models.ForeignKey(
        Vendor,
        verbose_name='Производитель',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='beers',
    )
    hops = models.ManyToManyField(
        Hop, verbose_name='Хмель', blank=True, related_name='beers'
    )

    class Meta:
        verbose_name = 'Пиво'
        verbose_name_plural = 'Пиво'
        ordering = ['name']

    def __str__(self):
        return self.name


class Rating(models.Model):
    """Оценка пива."""

    beer = models.ForeignKey(
        Beer, verbose_name='Пиво', on_delete=models.CASCADE, related_name='ratings'
    )
    score = models.PositiveSmallIntegerField('Оценка (1-10)')
    comment = models.TextField('Комментарий', blank=True)
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        verbose_name = 'Оценка'
        verbose_name_plural = 'Оценки'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.beer} — {self.score}/10'
