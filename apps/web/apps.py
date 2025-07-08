from django.apps import AppConfig

class WebConfig(AppConfig):
    name = 'apps.web'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import apps.web.signals