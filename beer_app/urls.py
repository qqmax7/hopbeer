"""Корневые URL-маршруты проекта beer_app."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('brewery.urls')),
]

urlpatterns += [
    path('accounts/', include('django.contrib.auth.urls')),
]

# Отдача медиафайлов (загруженные картинки пива) в dev-режиме
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)