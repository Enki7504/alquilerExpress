from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Importaciones de modelos locales
from ..models import (
    Reserva,
    Estado,
    ClienteInmueble,  # ← Agregar
)
from ..utils import crear_notificacion  # ← Agregar

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
    from ..utils import crear_notificacion  # ← Agregar import
    from ..models import ClienteInmueble      # ← Agregar import

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
        reserva_id = payment.get("external_reference")
        if reserva_id:
            try:
                reserva = Reserva.objects.get(id_reserva=reserva_id)
                estado_pagada = Estado.objects.get(nombre="Pagada")
                estado_cancelada = Estado.objects.get(nombre="Cancelada")
                
                # Cambiar estado de la reserva pagada
                reserva.estado = estado_pagada
                reserva.save()
                
                # ✅ NUEVO: Cancelar automáticamente reservas superpuestas
                # Para inmuebles
                if reserva.inmueble:
                    reservas_superpuestas = Reserva.objects.filter(
                        inmueble=reserva.inmueble,
                        estado__nombre__in=['Pendiente', 'Concurrente'],  # Estados que se pueden cancelar
                        fecha_inicio__lt=reserva.fecha_fin,
                        fecha_fin__gt=reserva.fecha_inicio
                    ).exclude(id_reserva=reserva.id_reserva)
                    
                    for r in reservas_superpuestas:
                        r.estado = estado_cancelada
                        r.save()
                        
                        # Notificar al cliente afectado
                        cliente_rel = ClienteInmueble.objects.filter(reserva=r).first()
                        if cliente_rel:
                            crear_notificacion(
                                usuario=cliente_rel.cliente,
                                mensaje=f"Tu reserva #{r.id_reserva} para '{reserva.inmueble.nombre}' del {r.fecha_inicio.strftime('%d/%m/%Y')} al {r.fecha_fin.strftime('%d/%m/%Y')} fue cancelada automáticamente porque se pagó otra reserva en fechas superpuestas."
                            )
                
                # Para cocheras
                elif reserva.cochera:
                    reservas_superpuestas = Reserva.objects.filter(
                        cochera=reserva.cochera,
                        estado__nombre__in=['Pendiente', 'Concurrente'],  # Estados que se pueden cancelar
                        fecha_inicio__lt=reserva.fecha_fin,
                        fecha_fin__gt=reserva.fecha_inicio
                    ).exclude(id_reserva=reserva.id_reserva)
                    
                    for r in reservas_superpuestas:
                        r.estado = estado_cancelada
                        r.save()
                        
                        # Notificar al cliente afectado
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