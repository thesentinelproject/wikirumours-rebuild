from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse


def account_verification_email(request, token, email):
    to = email
    link = (
        "http://"
        + request.get_host()
        + reverse("account_verification", kwargs={"token": token})
    )
    text_content = render_to_string("emails/account_verification.txt", {"link": link})
    html_content = render_to_string("emails/account_verification.html", {"link": link})
    send_mail(
        'Wikirumours account activation',
        text_content,
        'support@wikirumours.org',
        [to],
        fail_silently=False,
        html_message=html_content
    )
    return None


def forgot_password_verification(request, token, email):
    to = email
    link = (
        "http://"
        + request.get_host()
        + reverse("reset_password", kwargs={"token": token})
    )
    text_content = render_to_string("emails/forgot_password_verification.txt", {"link": link})
    html_content = render_to_string("emails/forgot_password_verification.html", {"link": link})
    send_mail(
        'Wikirumours password reset',
        text_content,
        'support@wikirumours.org',
        [to],
        fail_silently=False,
        html_message=html_content
    )
    return None


def overdue_reports_reminder(overdue_reports, user):
    to = user.email

    context = {
        'overdue_reports': overdue_reports[0:10],
        'user': user
    }

    text_content = render_to_string("emails/overdue_reports_reminder.txt", context=context)
    html_content = render_to_string("emails/overdue_reports_reminder.html", context=context)
    send_mail(
        f'Wikirumours - You have {overdue_reports.count()} overdue tasks',
        text_content,
        'support@wikirumours.org',
        [to],
        fail_silently=False,
        html_message=html_content
    )
    return None


def new_report_alert(report):
    # admins and moderators for the report's domain
    from users.models import User

    recipients = User.objects.filter(role__in=[User.ADMIN, User.MODERATOR], role_domains=report.domain, enable_email_notifications=True)

    context = {
        'report': report,
    }

    text_content = render_to_string("emails/new_report_alert.txt", context=context)
    html_content = render_to_string("emails/new_report_alert.html", context=context)
    send_mail(
        f'Wikirumours - New report submitted',
        text_content,
        'support@wikirumours.org',
        [recipient.email for recipient in recipients],
        fail_silently=True,
        html_message=html_content
    )
    return None


