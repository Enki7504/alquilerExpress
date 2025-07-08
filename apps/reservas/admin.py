# admin.py
from django.contrib import admin
from .models import Reserva, ReservaEstado, ClienteInmueble, Huesped

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id_reserva', 'inmueble', 'cochera', 'fecha_inicio', 'fecha_fin', 'estado', 'creada_en')
    search_fields = ('id_reserva', 'inmueble__nombre', 'cochera__nombre')

@admin.register(ReservaEstado)
class ReservaEstadoAdmin(admin.ModelAdmin):
    list_display = ('reserva', 'estado', 'fecha')
    list_filter = ('estado',)

@admin.register(ClienteInmueble)
class ClienteInmuebleAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'inmueble', 'cochera', 'reserva')
    search_fields = ('cliente__usuario__username',)

@admin.register(Huesped)
class HuespedAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni', 'fecha_nacimiento', 'reserva')
    search_fields = ('nombre', 'apellido', 'dni', 'reserva__id_reserva')
