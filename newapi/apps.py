from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NewapiConfig(AppConfig):
    name = 'newapi'
    verbose_name = _("new api")
