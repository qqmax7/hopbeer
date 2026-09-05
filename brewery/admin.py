"""Регистрация моделей в админке Django."""
from django.contrib import admin

from .models import Beer, Hop, Rating, Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'website')
    search_fields = ('name', 'country')


@admin.register(Hop)
class HopAdmin(admin.ModelAdmin):
    list_display = ('name', 'alpha_acid')
    search_fields = ('name',)


class RatingInline(admin.TabularInline):
    model = Rating
    extra = 0


@admin.register(Beer)
class BeerAdmin(admin.ModelAdmin):
    list_display = ('name', 'style', 'abv', 'ibu', 'vendor')
    list_filter = ('style', 'vendor')
    search_fields = ('name', 'style')
    filter_horizontal = ('hops',)
    inlines = [RatingInline]


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('beer', 'score', 'created_at')
    list_filter = ('score',)
