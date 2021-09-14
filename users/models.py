import datetime
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.urls import reverse

from countries.models import Country
from report.models import Domain, Report, PriorityChoice, StatusChoice

# Create your models here.
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _


def generate_password_reset_token():
    return get_random_string(16)


class User(AbstractUser):
    # TODO: allowed_domains to be added for other roles.
    END_USER = "End User"
    SUPPORT = "Support"
    MODERATOR = "Moderator"
    COMMUNITY_LIAISON = "Community Liaison"
    ADMIN = "Admin"

    ROLES_CHOICES = (
        (END_USER, END_USER),
        (SUPPORT, SUPPORT),
        (MODERATOR, MODERATOR),
        (COMMUNITY_LIAISON, COMMUNITY_LIAISON),
        (ADMIN, ADMIN),
    )

    sign_up_domain = models.ForeignKey(
        Domain,
        on_delete=models.SET_NULL,
        related_name="%(class)s_assigned_to",
        null=True,
        blank=True,
    )
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(
        _("email address"),
        unique=True,
        error_messages={
            "unique": _("A user with that email already exists."),
        },
    )
    api_key = models.CharField(max_length=20, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_user_anonymous = models.BooleanField(
        default=False,
        help_text=_(
            "If this is set to true, your name will not be displayed on reports submitted by you."
        ),
    )
    is_dark_mode_enabled = models.BooleanField(default=False)
    address = models.CharField(max_length=250, null=True, blank=True)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, blank=True
    )
    location = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=200, choices=ROLES_CHOICES, default=END_USER)
    role_domains = models.ManyToManyField(Domain, blank=True)

    enable_email_reminders = models.BooleanField(default=False,
                                                 help_text="Enable email reminders for overdue tasks for this user (irrelevant in case of end users).")

    enable_email_notifications = models.BooleanField(default=False,
                                                 help_text="Enable email notificiations for new reports for this user (irrelevant in case of end users).")
    api_post_access = models.BooleanField(default=False, help_text="Allowed to create POST requests via API")

    watchlisted_reports = models.ManyToManyField(Report, blank=True)
    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    is_authenticated = True
    is_anonymous = False

    def __str__(self):
        if not self.first_name and not self.last_name:
            return self.username
        return self.full_name

    @property
    def full_name(self):
        if not self.first_name and not self.last_name:
            return None
        return '%s %s' % (self.first_name, self.last_name)

    def get_overdue_tasks(self):
        overdue_task_ids = []
        for report in self.get_tasks():
            if report.is_overdue:
                overdue_task_ids.append(report.id)
        return Report.objects.filter(id__in=overdue_task_ids)

    def get_tasks(self, domain=None):
        from django.db.models import Q
        if self.role == User.COMMUNITY_LIAISON:
            reports = Report.objects.filter(assigned_to=self)
        elif self.role == User.MODERATOR or self.role == User.ADMIN:
            reports = Report.objects.filter(Q(assigned_to__isnull=True) | Q(assigned_to=self))
        else:
            reports = Report.objects.none()

        # reports = reports.filter(Q(resolution__isnull=True) | Q(resolution=""))
        reports = reports.filter(Q(status__name__icontains='new') | Q(status__name__icontains='investigat'))
        if domain and not domain.is_root_domain:
            reports = reports.filter(domain=domain)

        return reports

    def get_tasks_count(self, domain):
        return self.get_tasks(domain).count()

    def can_edit_report(self, report):
        if self.role == User.COMMUNITY_LIAISON:
            return report.assigned_to == self
        elif self.role == User.MODERATOR or self.role == User.ADMIN:
            return self.role_domains.filter(domain=report.domain).exists()
        else:
            return False

    def can_edit_sighting(self, sighting):
        if self.role == User.MODERATOR or self.role == User.ADMIN:
            return self.role_domains.filter(domain=sighting.report.domain).exists()
        else:
            return False

    def can_delete_comment(self, comment):
        if self.role in [User.MODERATOR, User.ADMIN]:
            return True
        elif comment.user == self:
            return True
        else:
            return False

    @property
    def absolute_url(self):
        return reverse('view_user', kwargs={'username': self.username})

    @property
    def get_full_name(self):
        return self.first_name + " " + self.last_name


class AccountActivationToken(models.Model):
    email = models.EmailField(max_length=255, null=False)
    token = models.CharField(max_length=255, default=generate_password_reset_token)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email


class BlacklistedIP(models.Model):
    ip_address = models.GenericIPAddressField()

    def __str__(self):
        return self.ip_address

    class Meta:
        verbose_name = "Blacklisted IP"
        verbose_name_plural = "Blacklisted IPs"
