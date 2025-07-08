from django.shortcuts import redirect
from django.urls import reverse

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