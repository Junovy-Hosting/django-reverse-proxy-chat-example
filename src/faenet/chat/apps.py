from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "faenet.chat"
    verbose_name = "Faerie Chat"

    def ready(self):
        from .presence import flush_all_presence

        flush_all_presence()
