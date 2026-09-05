"""Формы приложения brewery."""
from collections import Counter

from django import forms

from .models import Beer, Hop, Rating, Vendor


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['name', 'country', 'city', 'description', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }


class HopForm(forms.ModelForm):
    class Meta:
        model = Hop
        fields = ['name', 'alpha_acid', 'aroma', 'country', 'year']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'alpha_acid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aroma': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class BeerForm(forms.ModelForm):
    """Форма пива.

    Хмель выбирается одним полем `hops`: на телефоне — через поиск и теги.
    """

    hops = forms.ModelMultipleChoiceField(
        queryset=Hop.objects.all().order_by('name'),
        widget=forms.MultipleHiddenInput,
        required=False,
        label='Хмель',
    )

    class Meta:
        model = Beer
        fields = ['name', 'style', 'abv', 'ibu', 'og', 'value_deal', 'gost',
                  'description', 'vendor', 'hops']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название пива'}),
            'style': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Стиль'}),
            'abv': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Напр. 5.5'}),
            'ibu': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Напр. 40'}),
            'og': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Напр. 1050'}),
            'value_deal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0-10'}),
            'gost': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ГОСТ'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Вкус, аромат, впечатления'}),
            'vendor': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hops'].widget.attrs.setdefault('class', 'hops-hidden-input')
        if self.instance and self.instance.pk:
            selected = self.instance.hops.all()
            self.initial['hops'] = [h.pk for h in selected]

    def save(self, commit=True):
        beer = super().save(commit=commit)
        beer.hops.set(self.cleaned_data['hops'])
        return beer


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['beer', 'score', 'comment']
        widgets = {
            'beer': forms.Select(attrs={'class': 'form-control'}),
            'score': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
