from django.template.loader import render_to_string
from rest_framework.response import Response
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.conf import settings

def password_reset_token_created(request,sender, instance, reset_password_token, *args, **kwargs):
    current_site = get_current_site(request)
    mail_subject = "Password Reset for Wikirumours"
    message = render_to_string('newapi/password_reset_templates/user_reset_password.html', {
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.username,
        'email': reset_password_token.user.email,
        'domain' : current_site.domain,
        'token' : reset_password_token.key
    })
    msg_plain = render_to_string('newapi/password_reset_templates/user_reset_password.txt')
    email_sent_status = send_mail(mail_subject,msg_plain,settings.EMAIL_HOST_USER,[reset_password_token.user.email],html_message=message)
    if email_sent_status:
        return Response({"status":1,"message":"Please find reset link sent to your email"})
    return Response({"status":0,"message":"Reset link failed!"})

def password_reset_token_created_admin(request, reset_password_token, *args, **kwargs):
    current_site = get_current_site(request)
    mail_subject = "Password Reset for Wikirumours"
    message = render_to_string('newapi/password_reset_templates/user_reset_password.html', {
        'current_user': reset_password_token.user,
        'username': reset_password_token.user.username,
        'email': reset_password_token.user.email,
        'domain' : current_site.domain,
        'token' : reset_password_token.key
    })
    msg_plain = render_to_string('newapi/password_reset_templates/user_reset_password.txt')
    email_sent_status = send_mail(mail_subject,msg_plain,settings.EMAIL_HOST_USER,[reset_password_token.user.email],html_message=message)
    return email_sent_status
