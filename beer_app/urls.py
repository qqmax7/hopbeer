"""Корневые URL-маршруты проекта beer_app."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('brewery.urls')),
]