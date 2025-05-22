from django.contrib import admin

# Register your models here.
from .models import Cliente, Propiedad
from django.contrib.auth.models import User

admin.site.register(Cliente)
admin.site.register(Propiedad)
#User.objects.create_user(username='prueba', password='prueba')
