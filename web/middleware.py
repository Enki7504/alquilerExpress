from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from web.models import Reserva, Estado, ClienteInmueble
from web.utils import crear_notificacion
import logging

logger = logging.getLogger(__name__)

class BlockedUserMiddleware:
    """
    Middleware que muestra notificaciones a usuarios bloqueados
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificar si el usuario está autenticado pero bloqueado
        if (request.user.is_authenticated and 
            not request.user.is_active and 
            not request.user.is_staff):
            
            # No mostrar el mensaje en ciertas páginas
            excluded_paths = [
                reverse('logout'),
                reverse('login'),
            ]
            
            if request.path not in excluded_paths:
                messages.warning(request, 
                    "Tu cuenta está temporalmente limitada. No puedes realizar reservas, comentarios ni reseñas.")

        response = self.get_response(request)
        return response

class FirstLoginForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if (
                request.user.groups.filter(name__in=["firstloginempleado", "firstlogincliente"]).exists()
                and request.path != reverse("cambiar_contrasena")
                and not request.path.startswith("/admin/")
            ):
                return redirect("cambiar_contrasena")
        return self.get_response(request)

class RevisionAutomaticaMiddleware(MiddlewareMixin):
    """
    Middleware que ejecuta la revisión automática de reservas cada 1 minuto
    cuando cualquier usuario autenticado navega por el sitio
    """
    
    def process_request(self, request):
        # Ejecutar para TODOS los usuarios autenticados (clientes, empleados, staff)
        if request.user.is_authenticated:
            
            # Verificar si ya se ejecutó recientemente (cache de 1 minuto)
            cache_key = 'revision_automatica_ejecutada'
            if not cache.get(cache_key):
                try:
                    self.ejecutar_revision_automatica()
                    # Marcar como ejecutada por 1 minuto
                    cache.set(cache_key, True, 60)  # 60 segundos = 1 minuto
                    logger.info("Revisión automática ejecutada por navegación de usuario")
                except Exception as e:
                    logger.error(f"Error en revisión automática: {e}")
        
        return None
    
    def ejecutar_revision_automatica(self):
        """Ejecuta ambas funciones de revisión"""
        rechazadas = self.rechazar_reservas_pendientes()
        canceladas = self.cancelar_reservas_vencidas()
        
        if rechazadas > 0 or canceladas > 0:
            logger.info(f"Revisión automática completada: {rechazadas} rechazadas, {canceladas} canceladas")
            # Opcional: mostrar mensaje en la siguiente página (solo para staff/empleados)
            cache.set('revision_mensaje', {
                'rechazadas': rechazadas,
                'canceladas': canceladas
            }, 60)  # 1 minuto
    
    def rechazar_reservas_pendientes(self):
        """Rechazar reservas pendientes por más de 72 horas"""
        try:
            estado_pendiente = Estado.objects.get(nombre='Pendiente')
            estado_rechazada = Estado.objects.get(nombre='Rechazada')
            ahora = timezone.now()
            
            reservas = Reserva.objects.filter(
                estado=estado_pendiente,
                creada_en__lte=ahora - timezone.timedelta(hours=72)
            )
            
            count = reservas.count()
            
            for reserva in reservas:
                reserva.estado = estado_rechazada
                reserva.save()
                
                cliente_rel = ClienteInmueble.objects.filter(reserva=reserva).first()
                if cliente_rel:
                    crear_notificacion(
                        usuario=cliente_rel.cliente,
                        mensaje=f"Tu reserva #{reserva.id_reserva} fue rechazada por exceder las 72 horas de revisión."
                    )
            
            return count
        except Exception as e:
            logger.error(f"Error en rechazar_reservas_pendientes: {e}")
            return 0
    
    def cancelar_reservas_vencidas(self):
        """Cancelar reservas aprobadas que no se pagaron en 24 horas"""
        try:
            ahora = timezone.now()
            estado_aprobada = Estado.objects.get(nombre="Aprobada")
            estado_cancelada, _ = Estado.objects.get_or_create(nombre="Cancelada")
            
            reservas = Reserva.objects.filter(estado=estado_aprobada, aprobada_en__isnull=False)
            count = 0
            
            for reserva in reservas:
                if (ahora - reserva.aprobada_en).total_seconds() >= 24 * 3600:
                    reserva.estado = estado_cancelada
                    reserva.save()
                    
                    cliente_rel = ClienteInmueble.objects.filter(reserva=reserva).first()
                    if cliente_rel:
                        crear_notificacion(
                            usuario=cliente_rel.cliente,
                            mensaje=f"Tu reserva #{reserva.id_reserva} fue cancelada por no realizar el pago en 24 horas."
                        )
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"Error en cancelar_reservas_vencidas: {e}")
            return 0
