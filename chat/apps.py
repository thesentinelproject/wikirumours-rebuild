from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = 'chat'
    verbose_name = "Communication"

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('ChatMessage'))
