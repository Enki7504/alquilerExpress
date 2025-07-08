# admin.py
from django.contrib import admin
from .models import Tarjeta

@admin.register(Tarjeta)
class TarjetaAdmin(admin.ModelAdmin):
    list_display = ('id_tarjeta', 'nombre', 'numero', 'vencimiento', 'saldo')
    search_fields = ('nombre', 'numero')
