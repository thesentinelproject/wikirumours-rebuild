from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password, get_password_validators
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.conf import settings
from rest_framework import status, serializers, exceptions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from django_rest_passwordreset.serializers import EmailSerializer, PasswordTokenSerializer
from django_rest_passwordreset.models import ResetPasswordToken, clear_expired, get_password_reset_token_expiry_time, \
    get_password_reset_lookup_field
from django.shortcuts import render
from .password_reset_signal import password_reset_token_created, password_reset_token_created_admin
from django.contrib import messages
User = get_user_model()

HTTP_USER_AGENT_HEADER = getattr(settings, 'DJANGO_REST_PASSWORDRESET_HTTP_USER_AGENT_HEADER', 'HTTP_USER_AGENT')
HTTP_IP_ADDRESS_HEADER = getattr(settings, 'DJANGO_REST_PASSWORDRESET_IP_ADDRESS_HEADER', 'REMOTE_ADDR')

def CustomResetPasswordConfirm(request,token):
    if request.method == "GET":
        return render(request, 'newapi/password_reset_templates/password_change_form.html', {'token': token})
    elif request.method == 'POST':
        print("khelloooooo",request.POST['password'],request.POST['confirm_password'],request.POST['token'])
        serializer_class = PasswordTokenSerializer
        serializer = serializer_class(data=request.POST)
        try:
            serializer.is_valid()
        except ValidationError as e:
            messages.error(request, "Password "+e)
            return render(request, 'newapi/password_reset_templates/password_change_form.html', {'token': token,'error':"Password "+e})
        password = serializer.validated_data['password']
        token = serializer.validated_data['token']
        if request.POST['password'] != request.POST['confirm_password']:
            messages.error(request, "Both password must be same")
            return render(request, 'newapi/password_reset_templates/password_change_form.html', {'token': token,'error':"Both password must be same"})
        password_reset_token_validation_time = get_password_reset_token_expiry_time()
        reset_password_token = ResetPasswordToken.objects.filter(key=token).first()
        if reset_password_token is None:
            messages.error(request, "Token Not Found")
            return render(request, 'newapi/password_reset_templates/password_change_form.html', {'token': token,'error':"Token Not Found"})
        expiry_date = reset_password_token.created_at + timedelta(hours=password_reset_token_validation_time)
        if timezone.now() > expiry_date:
            reset_password_token.delete()
            messages.error(request, "Token Expired")
            return render(request, 'newapi/password_reset_templates/password_change_form.html', {'token': token,'error':"token expired"})
        if reset_password_token.user.eligible_for_reset():
            try:
                validate_password(
                    password,
                    user=reset_password_token.user,
                    password_validators=get_password_validators(settings.AUTH_PASSWORD_VALIDATORS)
                )
            except ValidationError as e:
                messages.error(request, e)
                return render(request, 'newapi/password_reset_templates/password_change_form.html', {'token': token,'error':e})
            reset_password_token.user.set_password(password)
            reset_password_token.user.save()
        ResetPasswordToken.objects.filter(user=reset_password_token.user).delete()
        return render(request, 'newapi/password_reset_templates/password_reset_done.html', {'token': token,'message':'Your Password is changed!'})

class ResetPasswordRequestToken(GenericAPIView):
    """
    An Api View which provides a method to request a password reset token based on an e-mail address

    Sends a signal reset_password_token_created when a reset token was created
    """
    throttle_classes = ()
    permission_classes = ()
    serializer_class = EmailSerializer
    request = ""
    def post(self, request, *args, **kwargs):
        print("herer")
        serializer = self.serializer_class(data=request.data)
        # serializer.is_valid(raise_exception=True)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password_reset_token_validation_time = get_password_reset_token_expiry_time()

            now_minus_expiry_time = timezone.now() - timedelta(hours=password_reset_token_validation_time)

            clear_expired(now_minus_expiry_time)

            users = User.objects.filter(**{'{}__iexact'.format(get_password_reset_lookup_field()): email})

            active_user_found = False
            for user in users:
                if user.eligible_for_reset():
                    active_user_found = True

            if not active_user_found and not getattr(settings, 'DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE', False):
                return Response({'status':0,'message':'Email address is not registered'})
            for user in users:
                if user.eligible_for_reset():
                    token = None
                    if user.password_reset_tokens.all().count() > 0:
                        token = user.password_reset_tokens.all()[0]
                    else:
                        token = ResetPasswordToken.objects.create(
                            user=user,
                            user_agent=request.META.get(HTTP_USER_AGENT_HEADER, ''),
                            ip_address=request.META.get(HTTP_IP_ADDRESS_HEADER, ''),
                        )
                    print("dsfsfsf")
                    password_reset_token_created(sender=self.__class__, instance=self, reset_password_token=token,request=request)
            return Response({'status': 1,'message':'A password reset link has been sent to your email address'})
        else:
            return Response({'status': 0,'message':'Please provide valid email address'})

def CustomResetPasswordRequestToken(request,email):
    password_reset_token_validation_time = get_password_reset_token_expiry_time()
    now_minus_expiry_time = timezone.now() - timedelta(hours=password_reset_token_validation_time)
    clear_expired(now_minus_expiry_time)
    users = User.objects.filter(**{'{}__iexact'.format(get_password_reset_lookup_field()): email})
    active_user_found = False
    for user in users:
        if user.eligible_for_reset():
            active_user_found = True
    if not active_user_found and not getattr(settings, 'DJANGO_REST_PASSWORDRESET_NO_INFORMATION_LEAKAGE', False):
        return 0
    for user in users:
        if user.eligible_for_reset():
            token = None
            if user.password_reset_tokens.all().count() > 0:
                token = user.password_reset_tokens.all()[0]
            else:
                token = ResetPasswordToken.objects.create(
                    user=user,
                    user_agent=request.META.get(HTTP_USER_AGENT_HEADER, ''),
                    ip_address=request.META.get(HTTP_IP_ADDRESS_HEADER, ''),
                )
            status = password_reset_token_created_admin(reset_password_token=token,request=request)
    return status

reset_password_request_token = ResetPasswordRequestToken.as_view()
