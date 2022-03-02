import datetime

from colorfield.fields import ColorField
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.crypto import get_random_string
from taggit_selectize.managers import TaggableManager

from countries.models import Country
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError


#
# Create your models here.


class Domain(models.Model):
    name = models.CharField(max_length=200, null=True, blank=True)
    domain = models.CharField(max_length=200)
    # default_language = models.CharField(max_length=200, null=True, blank=True)
    is_root_domain = models.BooleanField(default=False)
    logo = models.ImageField("Logo", null=True, blank=True)
    index_cms_page = models.ForeignKey('CMSPage', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.domain


class CMSPage(models.Model):
    title = models.CharField(max_length=200)
    visible_to_domains = models.ManyToManyField(Domain, blank=True)
    internal_title = models.CharField(max_length=200)
    content_slug = models.CharField(max_length=200)
    html_content = models.TextField(null=True, blank=True)
    css_content = models.TextField(null=True, blank=True)
    js_content = models.TextField(null=True, blank=True)
    is_visible = models.BooleanField(default=True)
    show_in_header = models.BooleanField(default=False)
    show_in_footer = models.BooleanField(default=False)
    show_in_sidebar = models.BooleanField(default=False)
    sequence_number = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["sequence_number"]
        verbose_name = 'Content Block'


class BlogPage(models.Model):
    title = models.CharField(max_length=200)
    visible_to_domains = models.ManyToManyField(Domain, blank=True)
    internal_title = models.CharField(max_length=200)
    content_slug = models.CharField(max_length=200)
    html_content = models.TextField(null=True, blank=True)
    css_content = models.TextField(null=True, blank=True)
    js_content = models.TextField(null=True, blank=True)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sequence_number = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["sequence_number"]
        verbose_name = 'Article'


class PriorityChoice(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)
    sequence_number = models.IntegerField(null=True, blank=True)
    number_of_days_before_alert = models.IntegerField(null=True, blank=True,
                                                      help_text="Number of days after which a user should be alerted about reports of this priority level")
    colour = ColorField(default='#FF0000')
    icon = models.CharField(max_length=255, null=True, blank=True,
                            help_text="Select a valid unicon descriptor eg: uil-arrow-up")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["sequence_number"]
        verbose_name = "Priority"
        verbose_name_plural = "Priorities"


class SourceChoice(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Source"
        verbose_name_plural = "Sources"


class StatusChoice(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)
    sequence_number = models.IntegerField(null=True, blank=True)
    colour = ColorField(default='#FF0000')
    icon = models.CharField(max_length=255, null=True, blank=True,
                            help_text="Select a valid unicon descriptor eg: uil-arrow-up")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["sequence_number"]
        verbose_name = "Status"
        verbose_name_plural = "Statuses"


class ReportedViaChoice(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Reported Via"
        verbose_name_plural = "Reported Via"


class OverheardAtChoice(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False, unique=True)

    def __str__(self):
        return self.name


def generate_public_key():
    return get_random_string(6)


class Report(models.Model):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"
    UNINVESTIGATED = "New / uninvestigated"
    UNDER_INVESTIGATION = "Under investigation"
    PROBABLY_TRUE = "Probably true"
    PROBABLY_FALSE = "Probably false"
    CONFIRMED_TRUE = "Confirmed true"
    CONFIRMED_FALSE = "Confirmed false"
    IMPOSSIBLE_TO_VERIFY = "Impossible to verify"
    IMPOSSIBLE_TO_VERIFY_BUT_PROBABLY_TRUE = "Impossible to verify but probably true"
    IMPOSSIBLE_TO_VERIFY_BUT_PROBABLY_FALSE = "Impossible to verify but probably false"

    PRIORITY_CHOICES = (
        (LOW, LOW),
        (MEDIUM, MEDIUM),
        (HIGH, HIGH),
        (VERY_HIGH, VERY_HIGH),
    )

    STATUS_CHOICES = (
        (UNINVESTIGATED, UNINVESTIGATED),
        (UNDER_INVESTIGATION, UNDER_INVESTIGATION),
        (PROBABLY_TRUE, PROBABLY_TRUE),
        (PROBABLY_FALSE, PROBABLY_FALSE),
        (CONFIRMED_TRUE, CONFIRMED_TRUE),
        (CONFIRMED_FALSE, CONFIRMED_FALSE),
        (IMPOSSIBLE_TO_VERIFY, IMPOSSIBLE_TO_VERIFY),
        (
            IMPOSSIBLE_TO_VERIFY_BUT_PROBABLY_TRUE,
            IMPOSSIBLE_TO_VERIFY_BUT_PROBABLY_TRUE,
        ),
        (
            IMPOSSIBLE_TO_VERIFY_BUT_PROBABLY_FALSE,
            IMPOSSIBLE_TO_VERIFY_BUT_PROBABLY_FALSE,
        ),
    )
    title = models.TextField()
    public_id = models.CharField(max_length=6, default=generate_public_key, unique=True,db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_assigned_to",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_reported_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    priority = models.ForeignKey(
        PriorityChoice, null=True, blank=False, on_delete=models.SET_NULL
    )
    status = models.ForeignKey(
        StatusChoice, null=True, blank=False, on_delete=models.SET_NULL
    )
    resolution = models.TextField(null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    location = gis_models.PointField(
        help_text="Use map widget for point the house location", null=True
    )
    tags = TaggableManager(blank=True)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    recently_edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_recently_edited_by",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    occurred_on = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    def clean(self):
        if not self.resolution and self.status:
            if not (str(self.status) == self.UNDER_INVESTIGATION) and not (str(self.status) == self.UNINVESTIGATED):
                raise ValidationError('Resolution is required for the selected status')


    @property
    def is_overdue(self):
        # if self.updated_at and self.priority and self.priority.number_of_days_before_alert:
        #     return True
        if self.updated_at and self.priority and self.priority.number_of_days_before_alert:
            return (datetime.datetime.now().replace(tzinfo=None) - self.updated_at.replace(
                tzinfo=None)).days > self.priority.number_of_days_before_alert
        else:
            return False

    @property
    def sightings_count(self):
        return self.sighting_set.count()


    @property
    def absolute_url(self):
        return reverse('view_report', kwargs={'report_public_id': self.public_id})

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-updated_at"]

    # Added to get reverse admin urls to work
    @property
    def app_label(self):
        return 'report'

    @property
    def model_name(self):
        return 'report'

    def save(self, *args, **kwargs):
        if not self.priority and not self.status:
            self.priority =  PriorityChoice.objects.filter(name='High').first()
            self.status =  StatusChoice.objects.filter(name='New / uninvestigated').first()
        super(Report, self).save()
    



class Sighting(models.Model):
    SMS = "SMS"
    EMAIL = "email"
    IN_PERSON = "in-person"
    INTERNET = "Internet"
    NA = "NA"
    TEMPLE = "temple"
    MARKET = "market"
    WHATSAPP = "whatsapp"
    FACEBOOK = "facebook"
    OVERHEARD = "overheard"
    WORKPLACE = "workplace"
    NEIGHBOURHOOD = "neighbourhood"
    STREET = "street"
    TELEPHONE = "telephone"
    OTHER = "other"

    REPORTED_CHOICES = (
        (INTERNET, INTERNET),
        (SMS, SMS),
        (OTHER, OTHER),
        (TELEPHONE, TELEPHONE),
        (EMAIL, EMAIL),
        (IN_PERSON, IN_PERSON),
    )
    OVERHEARD_CHOICES = (
        (NA, NA),
        (TEMPLE, TEMPLE),
        (MARKET, MARKET),
        (NEIGHBOURHOOD, NEIGHBOURHOOD),
        (WORKPLACE, WORKPLACE),
        (STREET, STREET),
    )

    SOURCE_CHOICES = (
        (WHATSAPP, WHATSAPP),
        (FACEBOOK, FACEBOOK),
        (OVERHEARD, OVERHEARD),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now=True)
    is_first_sighting = models.BooleanField(default=False)
    source = models.ForeignKey(
        SourceChoice, null=True, blank=True, on_delete=models.SET_NULL
    )
    reported_via = models.ForeignKey(
        ReportedViaChoice, null=True, blank=True, on_delete=models.SET_NULL
    )
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    location = gis_models.PointField(
        help_text="Use map to point the location of the sighting.", null=True
    )
    overheard_at = models.ForeignKey(
        OverheardAtChoice, null=True, blank=True, on_delete=models.SET_NULL
    )
    heard_on = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.report.title

    # Added to get reverse admin urls to work
    @property
    def app_label(self):
        return 'report'

    @property
    def model_name(self):
        return 'sighting'


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    comment = models.TextField()
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.comment


class FlaggedComment(models.Model):
    flagged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.comment


class WatchlistedReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.full_name or self.user.username} - {self.report.public_id}'

    class Meta:
        verbose_name = "Watchlisted Report"
        verbose_name_plural = "Watchlisted Reports"


def get_report_public_id(instance, filename):
    file_path = '{report_public_id}/{filename}'.format(
        report_public_id=instance.report.public_id, filename=filename)
    return file_path


class EvidenceFile(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to=get_report_public_id, null=False, blank=False,max_length=500)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True,null=True)

    def __str__(self):
        return f'{self.file.name}'

    def filename(self):
        import os
        return os.path.basename(self.file.name)

    class Meta:
        verbose_name = "Evidence File"
        verbose_name_plural = "Evidence Files"

