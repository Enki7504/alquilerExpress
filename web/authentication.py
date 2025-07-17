from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomAuthBackend(ModelBackend):
    """
    Backend personalizado que permite autenticación de usuarios inactivos (bloqueados)
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return
        
        try:
            # Buscar el usuario sin importar si está activo o no
            user = User.objects.get(**{User.USERNAME_FIELD: username})
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            # Si no existe el usuario, ejecutar check_password para evitar timing attacks
            User().set_password(password)
            return None
    
    def get_user(self, user_id):
        try:
            # Retornar el usuario sin importar si está activo
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None