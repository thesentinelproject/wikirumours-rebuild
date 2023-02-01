from django.http import HttpResponse
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.views.generic import View
from django.core.mail import EmailMessage
from users.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect

class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            six.text_type(user.pk) + six.text_type(timestamp) +
            six.text_type(user.is_active)
        )
account_activation_token = TokenGenerator()

def send_confirmation_mail(request,user,to_email):
    current_site = get_current_site(request)
    mail_subject = 'Wikirumours account activation'
    message = render_to_string('newapi/signup/email_signup_new.html', {
        'user': user.email,
        'user_name':user.first_name,
        'domain': current_site.domain,
        'uid':urlsafe_base64_encode(force_bytes(user.pk)),
        'token':account_activation_token.make_token(user),
    })
    msg_plain = render_to_string('newapi/signup/email_signup.txt')
    email_sent_status = send_mail(mail_subject,msg_plain,settings.EMAIL_HOST_USER,[to_email],html_message=message)
    return email_sent_status



def verify_confirmation(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.is_verified = True
        user.save()
        # member_users = get_member_user(user)
        # if member_users:
        #     for item in member_users:
        #         item.member_status = "verified"
        #         item.save()
        # return render(request,"api/signup/signup_completed.html",{"message":"Thank you for your email confirmation.Try Login now"})
        return redirect('/en/login')
    else:
        return Response({"status": 1, "message": "something went wrong!"})

