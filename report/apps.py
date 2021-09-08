from django.apps import AppConfig


class ReportConfig(AppConfig):
    name = "report"

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('Report'))
        registry.register(self.get_model('Sighting'))
        registry.register(self.get_model('Comment'))
