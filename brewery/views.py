"""Представления приложения brewery (CRUD для всех моделей)."""
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import BeerForm, HopForm, RatingForm, SystemM2MForm, VendorForm
from .models import Beer, Hop, Rating, SystemM2M, Vendor


# ---------- Vendor ----------
class VendorListView(ListView):
    model = Vendor
    template_name = 'brewery/vendor_list.html'
    context_object_name = 'vendors'


class VendorCreateView(CreateView):
    model = Vendor
    form_class = VendorForm
    template_name = 'brewery/vendor_form.html'
    success_url = reverse_lazy('vendor_list')


class VendorUpdateView(UpdateView):
    model = Vendor
    form_class = VendorForm
    template_name = 'brewery/vendor_form.html'
    success_url = reverse_lazy('vendor_list')


class VendorDeleteView(DeleteView):
    model = Vendor
    template_name = 'brewery/vendor_confirm_delete.html'
    success_url = reverse_lazy('vendor_list')


# ---------- Hop ----------
class HopListView(ListView):
    model = Hop
    template_name = 'brewery/hop_list.html'
    context_object_name = 'hops'


class HopCreateView(CreateView):
    model = Hop
    form_class = HopForm
    template_name = 'brewery/hop_form.html'
    success_url = reverse_lazy('hop_list')


class HopUpdateView(UpdateView):
    model = Hop
    form_class = HopForm
    template_name = 'brewery/hop_form.html'
    success_url = reverse_lazy('hop_list')


class HopDeleteView(DeleteView):
    model = Hop
    template_name = 'brewery/hop_confirm_delete.html'
    success_url = reverse_lazy('hop_list')


# ---------- Beer ----------
class BeerListView(ListView):
    model = Beer
    template_name = 'brewery/beer_list.html'
    context_object_name = 'beers'


class BeerDetailView(DetailView):
    model = Beer
    template_name = 'brewery/beer_detail.html'
    context_object_name = 'beer'


class BeerCreateView(CreateView):
    model = Beer
    form_class = BeerForm
    template_name = 'brewery/beer_form.html'
    success_url = reverse_lazy('beer_list')


class BeerUpdateView(UpdateView):
    model = Beer
    form_class = BeerForm
    template_name = 'brewery/beer_form.html'
    success_url = reverse_lazy('beer_list')


class BeerDeleteView(DeleteView):
    model = Beer
    template_name = 'brewery/beer_confirm_delete.html'
    success_url = reverse_lazy('beer_list')


# ---------- Rating ----------
class RatingListView(ListView):
    model = Rating
    template_name = 'brewery/rating_list.html'
    context_object_name = 'ratings'


class RatingCreateView(CreateView):
    model = Rating
    form_class = RatingForm
    template_name = 'brewery/rating_form.html'
    success_url = reverse_lazy('rating_list')


class RatingUpdateView(UpdateView):
    model = Rating
    form_class = RatingForm
    template_name = 'brewery/rating_form.html'
    success_url = reverse_lazy('rating_list')


class RatingDeleteView(DeleteView):
    model = Rating
    template_name = 'brewery/rating_confirm_delete.html'
    success_url = reverse_lazy('rating_list')


# ---------- SystemM2M ----------
class SystemM2MListView(ListView):
    model = SystemM2M
    template_name = 'brewery/systemm2m_list.html'
    context_object_name = 'systems'


class SystemM2MCreateView(CreateView):
    model = SystemM2M
    form_class = SystemM2MForm
    template_name = 'brewery/systemm2m_form.html'
    success_url = reverse_lazy('systemm2m_list')


class SystemM2MUpdateView(UpdateView):
    model = SystemM2M
    form_class = SystemM2MForm
    template_name = 'brewery/systemm2m_form.html'
    success_url = reverse_lazy('systemm2m_list')


class SystemM2MDeleteView(DeleteView):
    model = SystemM2M
    template_name = 'brewery/systemm2m_confirm_delete.html'
    success_url = reverse_lazy('systemm2m_list')


# ---------- Главная ----------
def index(request):
    """Главная страница со ссылками на все разделы."""
    return render(request, 'brewery/index.html', {
        'beer_count': Beer.objects.count(),
        'hop_count': Hop.objects.count(),
        'vendor_count': Vendor.objects.count(),
        'rating_count': Rating.objects.count(),
        'system_count': SystemM2M.objects.count(),
    })