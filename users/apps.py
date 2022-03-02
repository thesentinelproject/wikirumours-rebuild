from django.apps import AppConfig
from taggit.apps import TaggitAppConfig


class UserConfig(AppConfig):
    name = "users"

   
class WikirumoursTaggitConfig(TaggitAppConfig):
    verbose_name = "Keywords"
