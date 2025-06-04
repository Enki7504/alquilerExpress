from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import Reserva
from .models import Perfil
from .utils import enviar_mail_a_empleados_sobre_reserva

@receiver(post_save, sender=Reserva)
def enviar_mail_automatica_reserva(sender, instance, created, **kwargs):
    if created:
        enviar_mail_a_empleados_sobre_reserva(instance.id_reserva)