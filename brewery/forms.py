"""Формы приложения brewery."""
from django import forms

from .models import Beer, Hop, Rating, SystemM2M, Vendor


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['name', 'country', 'website']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }


class HopForm(forms.ModelForm):
    class Meta:
        model = Hop
        fields = ['name', 'alpha_acid', 'aroma']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'alpha_acid': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'aroma': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BeerForm(forms.ModelForm):
    class Meta:
        model = Beer
        fields = ['name', 'style', 'abv', 'ibu', 'description', 'vendor', 'hops']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'style': forms.TextInput(attrs={'class': 'form-control'}),
            'abv': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ibu': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'vendor': forms.Select(attrs={'class': 'form-control'}),
            'hops': forms.CheckboxSelectMultiple(attrs={'class': 'form-control'}),
        }


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['beer', 'score', 'comment']
        widgets = {
            'beer': forms.Select(attrs={'class': 'form-control'}),
            'score': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SystemM2MForm(forms.ModelForm):
    class Meta:
        model = SystemM2M
        fields = ['name', 'beers']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'beers': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }