from actstream.apps import ActstreamConfig
from django.apps import AppConfig
from taggit.apps import TaggitAppConfig


class UserConfig(AppConfig):
    name = "users"

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('User'))


class WikirumoursActStreamConfig(ActstreamConfig):
    verbose_name = "Logs"


class WikirumoursTaggitConfig(TaggitAppConfig):
    verbose_name = "Keywords"
