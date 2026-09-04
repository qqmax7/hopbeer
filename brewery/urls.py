"""URL-маршруты приложения brewery."""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # Vendor
    path('vendors/', views.VendorListView.as_view(), name='vendor_list'),
    path('vendors/create/', views.VendorCreateView.as_view(), name='vendor_create'),
    path('vendors/<int:pk>/edit/', views.VendorUpdateView.as_view(), name='vendor_update'),
    path('vendors/<int:pk>/delete/', views.VendorDeleteView.as_view(), name='vendor_delete'),

    # Hop
    path('hops/', views.HopListView.as_view(), name='hop_list'),
    path('hops/create/', views.HopCreateView.as_view(), name='hop_create'),
    path('hops/<int:pk>/edit/', views.HopUpdateView.as_view(), name='hop_update'),
    path('hops/<int:pk>/delete/', views.HopDeleteView.as_view(), name='hop_delete'),

    # Beer
    path('beers/', views.BeerListView.as_view(), name='beer_list'),
    path('beers/create/', views.BeerCreateView.as_view(), name='beer_create'),
    path('beers/<int:pk>/', views.BeerDetailView.as_view(), name='beer_detail'),
    path('beers/<int:pk>/edit/', views.BeerUpdateView.as_view(), name='beer_update'),
    path('beers/<int:pk>/delete/', views.BeerDeleteView.as_view(), name='beer_delete'),

    # Rating
    path('ratings/', views.RatingListView.as_view(), name='rating_list'),
    path('ratings/create/', views.RatingCreateView.as_view(), name='rating_create'),
    path('ratings/<int:pk>/edit/', views.RatingUpdateView.as_view(), name='rating_update'),
    path('ratings/<int:pk>/delete/', views.RatingDeleteView.as_view(), name='rating_delete'),

    # SystemM2M
    path('systems/', views.SystemM2MListView.as_view(), name='systemm2m_list'),
    path('systems/create/', views.SystemM2MCreateView.as_view(), name='systemm2m_create'),
    path('systems/<int:pk>/edit/', views.SystemM2MUpdateView.as_view(), name='systemm2m_update'),
    path('systems/<int:pk>/delete/', views.SystemM2MDeleteView.as_view(), name='systemm2m_delete'),
]