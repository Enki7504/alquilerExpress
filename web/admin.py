from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Perfil,
    Estado,
    Inmueble,
    Cochera,
    Reserva,
    ReservaEstado,
    InmuebleEstado,
    ClienteInmueble,
    Resenia,
    Comentario,
    InmuebleImagen,
    CocheraImagen,
    Provincia,
    Ciudad,
    Notificacion,
    Huesped,
    Tarjeta
)

# --- Inlines para mostrar imágenes asociadas ---
class InmuebleImagenInline(admin.TabularInline):
    model = InmuebleImagen
    extra = 1

class CocheraImagenInline(admin.TabularInline):
    model = CocheraImagen
    extra = 1

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
    inlines = [InmuebleImagenInline]

@admin.register(Cochera)
class CocheraAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'cantidad_vehiculos', 'precio_por_dia', 'estado')
    search_fields = ('nombre', 'ubicacion')
    list_filter = ('estado', 'con_techo')
    inlines = [CocheraImagenInline]

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id_reserva', 'inmueble', 'cochera', 'fecha_inicio', 'fecha_fin', 'estado', 'creada_en')
    search_fields = ('id_reserva', 'inmueble__nombre', 'cochera__nombre')

@admin.register(ReservaEstado)
class ReservaEstadoAdmin(admin.ModelAdmin):
    list_display = ('reserva', 'estado', 'fecha')
    list_filter = ('estado',)

@admin.register(InmuebleEstado)
class InmuebleEstadoAdmin(admin.ModelAdmin):
    list_display = ('inmueble', 'estado', 'fecha_inicio', 'fecha_fin')
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

@admin.register(Provincia)
class ProvinciaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'provincia')
    list_filter = ('provincia',)

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'mensaje', 'leido', 'fecha_creacion')
    list_filter = ('leido', 'fecha_creacion')
    search_fields = ('mensaje', 'usuario__usuario__username')
    ordering = ('-fecha_creacion',)

    # Opcional: Para mostrar mejor el nombre en el admin
    def get_model_perms(self, request):
        return {
            'add': self.has_add_permission(request),
            'change': self.has_change_permission(request),
            'delete': self.has_delete_permission(request),
            'view': self.has_view_permission(request),
        }

class HuespedInline(admin.TabularInline):
    model = Huesped
    extra = 0

@admin.register(Huesped)
class HuespedAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellido', 'dni', 'fecha_nacimiento', 'reserva')
    search_fields = ('nombre', 'apellido', 'dni', 'reserva__id_reserva')

@admin.register(Tarjeta)
class TarjetaAdmin(admin.ModelAdmin):
    list_display = ('id_tarjeta', 'nombre', 'numero', 'vencimiento', 'saldo')
    search_fields = ('nombre', 'numero')