from django.apps import AppConfig


class StatusConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'status'

    def ready(self):
        from . import metrics  # noqa: F401  (importing registers the gauge)