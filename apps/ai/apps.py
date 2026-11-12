from django.apps import AppConfig


class AIConfig(AppConfig):
    name = "apps.ai"
    verbose_name = "F1 AI Analyst"

    def ready(self):
        from . import checks
