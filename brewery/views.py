"""Представления приложения brewery (CRUD для всех моделей)."""
import json

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import BeerForm, HopForm, RatingForm, VendorForm
from .models import Beer, Hop, Rating, Vendor

# ---------- Vendor ----------
class VendorListView(LoginRequiredMixin, ListView):
    model = Vendor
    template_name = 'brewery/vendor_list.html'
    context_object_name = 'vendors'


class VendorCreateView(LoginRequiredMixin, CreateView):
    model = Vendor
    form_class = VendorForm
    template_name = 'brewery/vendor_form.html'
    success_url = reverse_lazy('vendor_list')


class VendorUpdateView(LoginRequiredMixin, UpdateView):
    model = Vendor
    form_class = VendorForm
    template_name = 'brewery/vendor_form.html'
    success_url = reverse_lazy('vendor_list')


class VendorDeleteView(LoginRequiredMixin, DeleteView):
    model = Vendor
    template_name = 'brewery/vendor_confirm_delete.html'
    success_url = reverse_lazy('vendor_list')


# ---------- Hop ----------
class HopListView(LoginRequiredMixin, ListView):
    model = Hop
    template_name = 'brewery/hop_list.html'
    context_object_name = 'hops'


class HopCreateView(LoginRequiredMixin, CreateView):
    model = Hop
    form_class = HopForm
    template_name = 'brewery/hop_form.html'
    success_url = reverse_lazy('hop_list')


class HopUpdateView(LoginRequiredMixin, UpdateView):
    model = Hop
    form_class = HopForm
    template_name = 'brewery/hop_form.html'
    success_url = reverse_lazy('hop_list')


class HopDeleteView(LoginRequiredMixin, DeleteView):
    model = Hop
    template_name = 'brewery/hop_confirm_delete.html'
    success_url = reverse_lazy('hop_list')


# ---------- Beer ----------
class BeerListView(LoginRequiredMixin, ListView):
    model = Beer
    template_name = 'brewery/beer_list.html'
    context_object_name = 'beers'


class BeerDetailView(LoginRequiredMixin, DetailView):
    model = Beer
    template_name = 'brewery/beer_detail.html'
    context_object_name = 'beer'


class BeerCreateView(LoginRequiredMixin, CreateView):
    model = Beer
    form_class = BeerForm
    template_name = 'brewery/beer_form.html'
    success_url = reverse_lazy('beer_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hops_json'] = json.dumps(
            [{'id': h.pk, 'name': h.name} for h in Hop.objects.all().order_by('name')],
            ensure_ascii=False
        )
        return ctx


class BeerUpdateView(LoginRequiredMixin, UpdateView):
    model = Beer
    form_class = BeerForm
    template_name = 'brewery/beer_form.html'
    success_url = reverse_lazy('beer_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hops_json'] = json.dumps(
            [{'id': h.pk, 'name': h.name} for h in Hop.objects.all().order_by('name')],
            ensure_ascii=False
        )
        return ctx


class BeerDeleteView(LoginRequiredMixin, DeleteView):
    model = Beer
    template_name = 'brewery/beer_confirm_delete.html'
    success_url = reverse_lazy('beer_list')


# ---------- Rating ----------
class RatingListView(LoginRequiredMixin, ListView):
    model = Rating
    template_name = 'brewery/rating_list.html'
    context_object_name = 'ratings'


class RatingCreateView(LoginRequiredMixin, CreateView):
    model = Rating
    form_class = RatingForm
    template_name = 'brewery/rating_form.html'
    success_url = reverse_lazy('rating_list')


class RatingUpdateView(LoginRequiredMixin, UpdateView):
    model = Rating
    form_class = RatingForm
    template_name = 'brewery/rating_form.html'
    success_url = reverse_lazy('rating_list')


class RatingDeleteView(LoginRequiredMixin, DeleteView):
    model = Rating
    template_name = 'brewery/rating_confirm_delete.html'
    success_url = reverse_lazy('rating_list')


# ---------- Главная ----------
def index(request):
    """Главная страница со ссылками на все разделы."""
    return render(request, 'brewery/index.html', {
        'beer_count': Beer.objects.count(),
        'hop_count': Hop.objects.count(),
        'vendor_count': Vendor.objects.count(),
        'rating_count': Rating.objects.count(),
    })