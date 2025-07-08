# admin.py
from django.contrib import admin
from .models import Inmueble, InmuebleEstado, InmuebleImagen

class InmuebleImagenInline(admin.TabularInline):
    model = InmuebleImagen
    extra = 1

@admin.register(Inmueble)
class InmuebleAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'precio_por_dia', 'estado')
    search_fields = ('nombre', 'direccion')
    list_filter = ('estado', 'cochera')
    inlines = [InmuebleImagenInline]

@admin.register(InmuebleEstado)
class InmuebleEstadoAdmin(admin.ModelAdmin):
    list_display = ('inmueble', 'estado', 'fecha_inicio', 'fecha_fin')
    list_filter = ('estado',)