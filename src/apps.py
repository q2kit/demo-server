from django.apps import AppConfig


class SrcConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src"
    verbose_name = "Services"

    def ready(self):
        import src.signals  # noqa
