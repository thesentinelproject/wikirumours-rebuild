from django.db import models
from users.models import User
from django.utils.translation import ugettext_lazy as _


class LoginDetail(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=25, blank=False, default="")
    mobile_os = models.CharField(max_length=25, blank=False, default="")
    mobile_token = models.CharField(max_length=250, blank=True)
    password = models.CharField(max_length=25, blank=True)
    social_login = models.BooleanField(default=False)
    mobile_login = models.BooleanField(default=False)
    # social_provider_id = models.CharField(max_length=300, blank=True, null=True)
    # social_provider = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        verbose_name = _('Login Detail')
