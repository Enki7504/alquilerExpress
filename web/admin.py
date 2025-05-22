from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Perfil,
    Estado,
    Inmueble,
    Cochera,
    InmuebleCochera,
    Reserva,
    ReservaEstado,
    InmuebleEstado,
    ClienteInmueble,
    Resenia,
    Comentario,
)

# Inline para mostrar Perfil dentro del admin de User
class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name_plural = 'Perfiles'

# Extender UserAdmin para incluir Perfil
class UserAdmin(BaseUserAdmin):
    inlines = (PerfilInline,)

# Primero, desregistramos User para luego registrarlo con la versión extendida
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Registrar otros modelos normalmente
@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'dni')
    search_fields = ('usuario__username', 'dni')

@admin.register(Estado)
class EstadoAdmin(admin.ModelAdmin):
    list_display = ('id_estado', 'nombre')
    search_fields = ('nombre',)

@admin.register(Inmueble)
class InmuebleAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ubicacion', 'precio_por_dia', 'estado')
    search_fields = ('nombre', 'ubicacion')
    list_filter = ('estado', 'cochera')

@admin.register(Cochera)
class CocheraAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cantidad_vehiculos', 'precio_por_dia', 'estado')
    search_fields = ('nombre', 'ubicacion')
    list_filter = ('estado', 'con_techo')

@admin.register(InmuebleCochera)
class InmuebleCocheraAdmin(admin.ModelAdmin):
    list_display = ('inmueble', 'cochera')
    search_fields = ('inmueble__nombre', 'cochera__nombre')

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id_reserva', 'fecha_inicio', 'fecha_fin', 'precio_total', 'estado')
    list_filter = ('estado',)
    search_fields = ('estado__nombre', 'descripcion')

@admin.register(ReservaEstado)
class ReservaEstadoAdmin(admin.ModelAdmin):
    list_display = ('reserva', 'estado', 'fecha')
    list_filter = ('estado',)

@admin.register(InmuebleEstado)
class InmuebleEstadoAdmin(admin.ModelAdmin):
    list_display = ('inmueble_cochera', 'estado', 'fecha_inicio', 'fecha_fin')
    list_filter = ('estado',)

@admin.register(ClienteInmueble)
class ClienteInmuebleAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'inmueble', 'cochera', 'reserva')
    search_fields = ('cliente__usuario__username',)

@admin.register(Resenia)
class ReseniaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'titulo', 'calificacion')
    search_fields = ('usuario__usuario__username', 'titulo')

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'descripcion')
    search_fields = ('usuario__usuario__username',)
