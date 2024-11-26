from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site




def account_verification_email(request, token, email):
    to = email
    link = (
        "http://"
        + get_current_site(request).domain
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
        + get_current_site(request).domain
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

    domain_name = str(report.domain)

    context = {
        'report': report,
    }

    text_content = render_to_string("emails/new_report_alert.txt", context=context)
    html_content = render_to_string("emails/new_report_alert.html", context=context)
    send_mail(
        f'{domain_name.capitalize()} - New report submitted',
        text_content,
        'support@wikirumours.org',
        [recipient.email for recipient in recipients],
        fail_silently=True,
        html_message=html_content
    )
    return None


def emergency_report_alert(report):
    # admins and moderators for the report's domain
    from report.models import WatchlistedReport
    mailing_list = []
    mailing_list.append(report.assigned_to.email)
    watchlist_emails = WatchlistedReport.objects.filter(report=report).values_list('user__email', flat=True)
    mailing_list.extend(watchlist_emails)
    domain_name = str(report.domain)
    context = {
        'report': report,
    }

    text_content = render_to_string("emails/emergency_report_alert.txt", context=context)
    html_content = render_to_string("emails/emergency_report_alert.html", context=context)
    send_mail(
        f'{domain_name.capitalize()} - Emergency report created',
        text_content,
        'support@wikirumours.org',
        mailing_list,
        fail_silently=True,
        html_message=html_content
    )
    return None



def api__key_email(request, email):
    to = email
    text_content = render_to_string("emails/api_key.txt", {})
    html_content = render_to_string("emails/api_key.html", {})
    send_mail(
        'Wikirumours Api Key Generation Alert',
        text_content,
        'support@wikirumours.org',
        [to],
        fail_silently=False,
        html_message=html_content
    )
    return None




def report_trigger_alert(report, mailing_list, subject, email_text):
    text_content = ''
    domain_name = str(report.domain)
    context = {
        'report': report,
        'email_text': email_text
    }
    html_content = render_to_string("emails/changes_report_alert.html", context=context)
    send_mail(
        f'{domain_name.capitalize()} - {subject}',
        text_content,
        'support@wikirumours.org',
        mailing_list,
        fail_silently=True,
        html_message=html_content
    )
    return None



def new_comment_alert(comment_obj, email_list):
    text_content = ''
    report = comment_obj.report
    domain_name = str(report.domain)
    context = {
        'report': report,
    }
    html_content = render_to_string("emails/new_comment_alert.html", context=context)
    send_mail(
        f'{domain_name.capitalize()} - New Comment Alert',
        text_content,
        'support@wikirumours.org',
        email_list,
        fail_silently=True,
        html_message=html_content
    )
    return None
