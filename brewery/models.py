"""Модели приложения brewery.

Схема адаптирована из обсуждения (Supabase) под локальную SQLite-базу.
"""
import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.images import get_image_dimensions
from django.db import models
from PIL import Image


# Максимальный размер (по длинной стороне) и качество JPEG для сжатия загружаемых картинок.
IMAGE_MAX_SIDE = 800
IMAGE_JPEG_QUALITY = 82


class Vendor(models.Model):
    """Производитель (пивоварня)."""

    name = models.CharField('Название', max_length=200)
    country = models.CharField('Страна', max_length=100, blank=True)
    city = models.CharField('Город', max_length=100, blank=True)
    description = models.TextField('Описание', blank=True)
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
    country = models.CharField('Страна', max_length=100, blank=True)
    year = models.PositiveSmallIntegerField('Год', null=True, blank=True)

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
    og = models.PositiveIntegerField('OG', null=True, blank=True)
    value_deal = models.DecimalField(
        'Цена/качество', max_digits=4, decimal_places=2, null=True, blank=True
    )
    gost = models.CharField('ГОСТ', max_length=100, blank=True)
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
    image = models.ImageField(
        'Картинка', upload_to='beers/', blank=True, null=True
    )

    class Meta:
        verbose_name = 'Пиво'
        verbose_name_plural = 'Пиво'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Сжимаем загруженную картинку: уменьшаем до IMAGE_MAX_SIDE и конвертируем в JPEG."""
        if self.image and self.image.file:
            try:
                img = Image.open(self.image.file)
                img = img.convert('RGB')
                img.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE), Image.LANCZOS)
                buf = BytesIO()
                img.save(buf, format='JPEG', quality=IMAGE_JPEG_QUALITY, optimize=True)
                name = os.path.splitext(os.path.basename(self.image.name))[0] + '.jpg'
                self.image.save(name, ContentFile(buf.getvalue()), save=False)
            except Exception:
                # Если файл не картинка или повреждён — оставляем как есть.
                pass
        super().save(*args, **kwargs)


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
