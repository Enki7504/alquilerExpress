from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

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