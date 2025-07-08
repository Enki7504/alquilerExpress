# admin.py
from django.contrib import admin
from .models import Cochera, CocheraImagen

class CocheraImagenInline(admin.TabularInline):
    model = CocheraImagen
    extra = 1

@admin.register(Cochera)
class CocheraAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cantidad_vehiculos', 'precio_por_dia', 'estado')
    search_fields = ('nombre', 'direccion')
    list_filter = ('estado', 'con_techo')
    inlines = [CocheraImagenInline]
