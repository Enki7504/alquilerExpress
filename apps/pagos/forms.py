# forms.py
from django import forms
from .models import Tarjeta

class TarjetaForm(forms.ModelForm):
    class Meta:
        model = Tarjeta
        fields = ['numero', 'nombre', 'vencimiento', 'cvv']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 16}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'vencimiento': forms.TextInput(attrs={'class': 'form-control'}),
            'cvv': forms.PasswordInput(attrs={'class': 'form-control', 'maxlength': 4}),
        }