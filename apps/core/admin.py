# admin.py
from django.contrib import admin
from .models import Estado, Provincia, Ciudad, Resenia, Comentario

@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('id_estado', 'nombre')
    search_fields = ('nombre',)

@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'provincia')
    list_filter = ('provincia',)

@admin.register(Resenia)
class ReseniaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'titulo', 'calificacion')
    search_fields = ('usuario__usuario__username', 'titulo')

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'descripcion')
    search_fields = ('usuario__usuario__username',)