from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404  # ✅ AGREGAR get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone  # ✅ AGREGAR timezone
from datetime import timedelta     # ✅ AGREGAR timedelta

# Importaciones de modelos locales
from ..models import (
    Reserva,
    Estado,
    ClienteInmueble,
    ExtensionReserva,  # ✅ AGREGAR ExtensionReserva
)
from ..utils import crear_notificacion

def crear_preferencia_mp(request):
    if request.method == "POST":
        import mercadopago
        import json
        from django.conf import settings
        from django.http import JsonResponse

        data = json.loads(request.body)
        monto = data.get('monto', 1000)
        descripcion = data.get('descripcion', 'Reserva Alquiler Express')
        id_reserva = data.get('id_reserva')

        # Verificar que la reserva esté en estado "Aprobada"
        try:
            reserva = Reserva.objects.get(id_reserva=id_reserva)
        except Reserva.DoesNotExist:
            return JsonResponse({"error": "Reserva no encontrada."}, status=404)

        if reserva.estado.nombre != "Aprobada":
            return JsonResponse({"error": "Solo se puede pagar una reserva en estado Aprobada."}, status=400)

        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        preference_data = {
            "items": [
                {
                    "title": descripcion,
                    "quantity": 1,
                    "unit_price": float(monto),
                }
            ],
            "back_urls": {
                "success": "https://reptile-genuine-redbird.ngrok-free.app/reservas/",
                "failure": "https://reptile-genuine-redbird.ngrok-free.app/reservas/",
                "pending": "https://reptile-genuine-redbird.ngrok-free.app/reservas/",
            },
            "auto_return": "approved",
            "external_reference": str(id_reserva),
            "notification_url": "https://reptile-genuine-redbird.ngrok-free.app/mercadopago/webhook/",
        }
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response.get("response", {})
        if "id" in preference:
            return JsonResponse({
                "id": preference["id"],
                "init_point": preference.get("init_point")
            })
        else:
            return JsonResponse({"error": preference.get("message", "Error al crear preferencia"), "detalle": preference}, status=400)

def probar_mp(request):
    return render(request, 'probar_mp.html', {
        'MERCADOPAGO_PUBLIC_KEY': settings.MERCADOPAGO_PUBLIC_KEY,
        'precio': 1000,  # o el valor que quieras probar
    })

@csrf_exempt
def mercadopago_webhook(request):
    import mercadopago
    import json
    from ..utils import crear_notificacion
    from ..models import ClienteInmueble, ExtensionReserva

    payment_id = None

    # Solo procesar si es topic=payment
    if request.GET.get("topic") == "payment" and request.GET.get("id"):
        payment_id = request.GET.get("id")
    elif request.GET.get("type") == "payment" and request.GET.get("data.id"):
        payment_id = request.GET.get("data.id")
    elif request.body:
        try:
            data = json.loads(request.body)
            payment_id = (
                data.get("data", {}).get("id")
                or data.get("id")
                or data.get("payment_id")
            )
        except Exception:
            pass

    if not payment_id:
        return JsonResponse({"success": True})

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    payment_info = sdk.payment().get(payment_id)
    payment = payment_info.get("response", {})

    if payment.get("status") == "approved":
        external_reference = payment.get("external_reference")
        if external_reference:
            
            # ✅ MANEJAR PAGOS DE EXTENSIONES
            if external_reference.startswith("extension_"):
                extension_id = external_reference.replace("extension_", "")
                try:
                    extension = ExtensionReserva.objects.get(id=extension_id)
                    
                    # Verificar que esté en estado Aprobada
                    if extension.estado.nombre == 'Aprobada':
                        # Marcar como pagada
                        estado_pagada = Estado.objects.get(nombre='Pagada')
                        extension.estado = estado_pagada
                        extension.fecha_pago = timezone.now()
                        extension.mp_payment_id = payment_id
                        extension.save()
                        
                        # Actualizar la reserva original
                        reserva = extension.reserva
                        reserva.fecha_fin = extension.fecha_fin_nueva
                        reserva.precio_total += extension.precio_extension
                        reserva.save()
                        
                        # Notificar al cliente
                        cliente = reserva.cliente()
                        if cliente:
                            tipo_propiedad = reserva.inmueble.nombre if reserva.inmueble else reserva.cochera.nombre
                            periodo_extension = f"{extension.dias_extension} días" if extension.dias_extension else f"{extension.horas_extension} horas"
                            
                            crear_notificacion(
                                usuario=cliente,
                                mensaje=f"¡Pago confirmado! Tu extensión de {periodo_extension} para la reserva #{reserva.id_reserva} "
                                       f"de '{tipo_propiedad}' ha sido confirmada. "
                                       f"Nueva fecha de finalización: {extension.fecha_fin_nueva.strftime('%d/%m/%Y %H:%M')}."
                            )
                        
                        print(f"✅ Extensión #{extension.id} pagada exitosamente")
                        return JsonResponse({"success": True})
                    
                except ExtensionReserva.DoesNotExist:
                    print(f"❌ Extensión no encontrada: {extension_id}")
                    return JsonResponse({"error": "Extensión no encontrada"}, status=404)
                except Exception as e:
                    print(f"❌ Error procesando pago de extensión: {str(e)}")
                    return JsonResponse({"error": f"Error interno: {str(e)}"}, status=500)
            
            # ✅ MANEJAR PAGOS DE RESERVAS NORMALES (código existente)
            else:
                try:
                    reserva = Reserva.objects.get(id_reserva=external_reference)
                    estado_pagada = Estado.objects.get(nombre="Pagada")
                    estado_cancelada = Estado.objects.get(nombre="Cancelada")
                    
                    # Cambiar estado de la reserva pagada
                    reserva.estado = estado_pagada
                    reserva.save()
                    
                    # Cancelar automáticamente reservas superpuestas (código existente)
                    if reserva.inmueble:
                        reservas_superpuestas = Reserva.objects.filter(
                            inmueble=reserva.inmueble,
                            estado__nombre__in=['Pendiente', 'Concurrente'],
                            fecha_inicio__lt=reserva.fecha_fin,
                            fecha_fin__gt=reserva.fecha_inicio
                        ).exclude(id_reserva=reserva.id_reserva)
                        
                        for r in reservas_superpuestas:
                            r.estado = estado_cancelada
                            r.save()
                            
                            cliente_rel = ClienteInmueble.objects.filter(reserva=r).first()
                            if cliente_rel:
                                crear_notificacion(
                                    usuario=cliente_rel.cliente,
                                    mensaje=f"Tu reserva #{r.id_reserva} para '{reserva.inmueble.nombre}' del {r.fecha_inicio.strftime('%d/%m/%Y')} al {r.fecha_fin.strftime('%d/%m/%Y')} fue cancelada automáticamente porque se pagó otra reserva en fechas superpuestas."
                                )
                    
                    elif reserva.cochera:
                        reservas_superpuestas = Reserva.objects.filter(
                            cochera=reserva.cochera,
                            estado__nombre__in=['Pendiente', 'Concurrente'],
                            fecha_inicio__lt=reserva.fecha_fin,
                            fecha_fin__gt=reserva.fecha_inicio
                        ).exclude(id_reserva=reserva.id_reserva)
                        
                        for r in reservas_superpuestas:
                            r.estado = estado_cancelada
                            r.save()
                            
                            cliente_rel = ClienteInmueble.objects.filter(reserva=r).first()
                            if cliente_rel:
                                crear_notificacion(
                                    usuario=cliente_rel.cliente,
                                    mensaje=f"Tu reserva #{r.id_reserva} para '{reserva.cochera.nombre}' del {r.fecha_inicio.strftime('%d/%m/%Y %H:%M')} al {r.fecha_fin.strftime('%d/%m/%Y %H:%M')} fue cancelada automáticamente porque se pagó otra reserva en horarios superpuestos."
                                )
                    
                    return JsonResponse({"success": True})
                except (Reserva.DoesNotExist, Estado.DoesNotExist) as e:
                    return JsonResponse({"error": f"Error al procesar pago: {str(e)}"}, status=404)
                except Exception as e:
                    return JsonResponse({"error": f"Error interno: {str(e)}"}, status=500)
    
    return JsonResponse({"success": False})

@login_required
def crear_preferencia_extension_mp(request, id_extension):
    """
    Crea una preferencia de MercadoPago para el pago de una extensión
    """
    extension = get_object_or_404(ExtensionReserva, id=id_extension)
    
    # Verificar que el usuario es el dueño de la reserva
    if not ClienteInmueble.objects.filter(cliente=request.user.perfil, reserva=extension.reserva).exists():
        return JsonResponse({'success': False, 'error': 'No tienes permisos para esta extensión.'}, status=403)
    
    # Verificar que la extensión esté aprobada
    if extension.estado.nombre != 'Aprobada':
        return JsonResponse({'success': False, 'error': 'Esta extensión no está disponible para pago.'}, status=400)
    
    if request.method == 'POST':
        try:
            import mercadopago
            from django.conf import settings
            
            # Configurar SDK de MercadoPago
            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            
            # Datos de la extensión
            reserva = extension.reserva
            cliente = reserva.cliente()
            tipo_propiedad = reserva.inmueble.nombre if reserva.inmueble else reserva.cochera.nombre
            periodo_extension = f"{extension.dias_extension} días" if extension.dias_extension else f"{extension.horas_extension} horas"
            
            # URLs de retorno - SIMPLES, solo redirigen al detalle de la reserva
            base_url = request.build_absolute_uri('/')[:-1]
            success_url = f"{base_url}/reservas/{reserva.id_reserva}/detalle/"
            failure_url = f"{base_url}/reservas/{reserva.id_reserva}/detalle/"
            pending_url = f"{base_url}/reservas/{reserva.id_reserva}/detalle/"
            
            # Crear preferencia
            preference_data = {
                "items": [
                    {
                        "title": f"Extensión de Reserva #{reserva.id_reserva}",
                        "description": f"Extensión de {periodo_extension} para {tipo_propiedad}",
                        "quantity": 1,
                        "currency_id": "ARS",
                        "unit_price": float(extension.precio_extension)
                    }
                ],
                "payer": {
                    "name": cliente.usuario.first_name if cliente else "",
                    "surname": cliente.usuario.last_name if cliente else "",
                    "email": cliente.usuario.email if cliente else "",
                },
                "back_urls": {
                    "success": success_url,
                    "failure": failure_url,
                    "pending": pending_url
                },
                "auto_return": "approved",
                "external_reference": f"extension_{extension.id}",
                "notification_url": f"{base_url}/mercadopago/webhook/",
                "statement_descriptor": "ALQUILER EXPRESS - EXT",
                "expires": True,
                "expiration_date_from": timezone.now().isoformat(),
                "expiration_date_to": (timezone.now() + timedelta(hours=24)).isoformat()
            }
            
            print(f"🔧 Creando preferencia MP para extensión #{extension.id}")
            print(f"   💰 Monto: ${extension.precio_extension}")
            print(f"   📧 Email: {cliente.usuario.email if cliente else 'N/A'}")
            
            # Crear preferencia en MercadoPago
            preference_response = sdk.preference().create(preference_data)
            preference = preference_response["response"]
            
            if preference_response["status"] == 201:
                print(f"✅ Preferencia creada exitosamente: {preference['id']}")
                
                # Guardar ID de preferencia en la extensión
                extension.mp_preference_id = preference['id']
                extension.save()
                
                return JsonResponse({
                    'success': True,
                    'preference_id': preference['id'],
                    'init_point': preference['init_point'],
                    'sandbox_init_point': preference.get('sandbox_init_point'),
                })
            else:
                print(f"❌ Error creando preferencia: {preference_response}")
                return JsonResponse({
                    'success': False, 
                    'error': 'Error al crear la preferencia de pago'
                }, status=500)
                
        except ImportError:
            return JsonResponse({
                'success': False, 
                'error': 'SDK de MercadoPago no configurado'
            }, status=500)
        except Exception as e:
            print(f"💥 Error en crear_preferencia_extension_mp: {str(e)}")
            return JsonResponse({
                'success': False, 
                'error': f'Error interno: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)