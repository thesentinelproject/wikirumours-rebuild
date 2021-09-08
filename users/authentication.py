from django.utils.translation import gettext as _
from rest_framework import authentication
from rest_framework import exceptions
from .models import User


class ApiAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):

        username = request.headers.get("username")
        api_key = request.headers.get("Api-key")

        if not username or not api_key:
            raise exceptions.AuthenticationFailed(_("No credentials provided."))

        user = {}
        try:
            # get the user
            user = User.objects.get(username=username, api_key=api_key)
        except User.DoesNotExist:
            # raise exception if user does not exist
            raise exceptions.AuthenticationFailed("No such user")

        if user is None:
            raise exceptions.AuthenticationFailed(
                _("Invalid username/password/api-key")
            )

        if not user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        return (user, None)
