"""Представления приложения brewery (CRUD для всех моделей)."""
import json

from django.db.models import Avg, Count, F, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
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

    def get_queryset(self):
        return (
            super().get_queryset()
            .select_related('vendor')
            .prefetch_related('hops')
            .annotate(
                ratings_count=Count('ratings'),
                avg_score=Avg('ratings__score'),
            )
            .prefetch_related(
                Prefetch(
                    'ratings',
                    queryset=Rating.objects.filter(owner=self.request.user),
                    to_attr='my_ratings',
                )
            )
        )


class BeerDetailView(LoginRequiredMixin, DetailView):
    model = Beer
    template_name = 'brewery/beer_detail.html'
    context_object_name = 'beer'

    def get_queryset(self):
        return super().get_queryset().select_related('vendor').prefetch_related('hops')


class HopsJsonMixin:
    """Добавляет в контекст JSON-список хмеля для виджета выбора."""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hops_json'] = json.dumps(
            [{'id': h.pk, 'name': h.name} for h in Hop.objects.all().order_by('name')],
            ensure_ascii=False
        )
        return ctx


class BeerCreateView(LoginRequiredMixin, HopsJsonMixin, CreateView):
    model = Beer
    form_class = BeerForm
    template_name = 'brewery/beer_form.html'
    success_url = reverse_lazy('beer_list')


class BeerUpdateView(LoginRequiredMixin, HopsJsonMixin, UpdateView):
    model = Beer
    form_class = BeerForm
    template_name = 'brewery/beer_form.html'
    success_url = reverse_lazy('beer_list')


class BeerDeleteView(LoginRequiredMixin, DeleteView):
    model = Beer
    template_name = 'brewery/beer_confirm_delete.html'
    success_url = reverse_lazy('beer_list')


# ---------- Rating ----------
class RatingListView(LoginRequiredMixin, ListView):
    """Страница «Оценки»: пользователь видит только свои оценки."""

    model = Rating
    template_name = 'brewery/rating_list.html'
    context_object_name = 'ratings'

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user).select_related('beer')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Сколько оценок всего (включая чужие) — чтобы было видно, куда делись остальные.
        context['rating_total'] = Rating.objects.count()
        return context


class RatingCreateView(LoginRequiredMixin, CreateView):
    model = Rating
    form_class = RatingForm
    template_name = 'brewery/rating_form.html'
    success_url = reverse_lazy('rating_list')

    def get_initial(self):
        """Ссылка «Оценить» в списке пива передаёт пиво в ?beer=<pk>."""
        initial = super().get_initial()
        beer_id = self.request.GET.get('beer')
        if beer_id and beer_id.isdigit():
            initial['beer'] = beer_id
        return initial

    def form_valid(self, form):
        # Владелец оценки — текущий пользователь (в форме поле не показывается).
        form.instance.owner = self.request.user
        return super().form_valid(form)


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
# Количество таблиц на странице отчёта (хмели и производители).
REPORT_TABLE_COUNT = 2


def index(request):
    """Главная страница со ссылками на все разделы."""
    ratings = Rating.objects.all()
    if request.user.is_authenticated:
        # Раздел «Оценки» показывает только свои оценки — счётчик должен совпадать с ним.
        ratings = ratings.filter(owner=request.user)
    return render(request, 'brewery/index.html', {
        'beer_count': Beer.objects.count(),
        'hop_count': Hop.objects.count(),
        'vendor_count': Vendor.objects.count(),
        'rating_count': ratings.count(),
        'report_table_count': REPORT_TABLE_COUNT,
    })


# ---------- Отчёт ----------
REPORT_LIMIT = 5


class ReportView(LoginRequiredMixin, TemplateView):
    """Страница «Отчёт»: топ-5 хмелей по средней оценке и топ-5 производителей по популярности."""

    template_name = 'brewery/report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hops'] = self._top_hops()
        context['vendors'] = self._top_vendors()
        return context

    def _top_hops(self):
        """Хмели с максимальной средней оценкой пива из них и примером лучшего пива."""
        hops = list(
            Hop.objects.annotate(
                beers_count=Count('beers', distinct=True),
                avg_score=Avg('beers__ratings__score'),
            )
            .filter(avg_score__isnull=False)
            .order_by(F('avg_score').desc(), F('beers_count').desc(), 'name')
            .prefetch_related(
                Prefetch(
                    'beers',
                    queryset=Beer.objects.annotate(avg_score=Avg('ratings__score'))
                    .filter(avg_score__isnull=False)
                    .order_by('-avg_score', 'name'),
                    to_attr='rated_beers',
                )
            )[:REPORT_LIMIT]
        )
        for hop in hops:
            hop.best_beer = hop.rated_beers[0] if hop.rated_beers else None
        return hops

    def _top_vendors(self):
        """Производители с наибольшим количеством пива и средней оценкой этого пива."""
        return (
            Vendor.objects.annotate(
                beers_count=Count('beers', distinct=True),
                avg_score=Avg('beers__ratings__score'),
            )
            .filter(beers_count__gt=0)
            .order_by(
                '-beers_count', F('avg_score').desc(nulls_last=True), 'name'
            )[:REPORT_LIMIT]
        )