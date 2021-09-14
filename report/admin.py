# from django.contrib import admin
from django.contrib import admin
from mapwidgets import GooglePointFieldWidget
from django.contrib.gis.db import models
from .models import Domain, Report, Sighting, Comment, PriorityChoice, SourceChoice, StatusChoice, ReportedViaChoice, \
    WatchlistedReport, CMSPage, BlogPage, EvidenceFile
from admin_auto_filters.filters import AutocompleteFilter


# # Register your models here.


class DomainAdmin(admin.ModelAdmin):
    model = Domain


class ReportAdmin(admin.ModelAdmin):
    model = Report
    list_display = ['title', 'domain', 'country', 'priority', 'status', 'reported_by']
    search_fields = ['title']
    formfield_overrides = {models.PointField: {"widget": GooglePointFieldWidget}}


class ReportFilter(AutocompleteFilter):
    title = 'Report'
    field_name = 'report'


class SightingAdmin(admin.ModelAdmin):
    model = Sighting
    list_filter = [ReportFilter]
    list_display = ['report', 'country', 'user']
    formfield_overrides = {models.PointField: {"widget": GooglePointFieldWidget}}


class StatusChoiceAdmin(admin.ModelAdmin):
    model = StatusChoice
    list_display = ['name', 'sequence_number']


class CommentsAdmin(admin.ModelAdmin):
    model = Comment


class EvidenceFileAdmin(admin.ModelAdmin):
    model = EvidenceFile
    list_filter = [ReportFilter]
    list_display = ['filename', 'is_public', 'report', ]



admin.site.register(Domain, DomainAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Sighting, SightingAdmin)
admin.site.register(Comment, CommentsAdmin)

admin.site.register(PriorityChoice)
admin.site.register(SourceChoice)
admin.site.register(StatusChoice, StatusChoiceAdmin)
admin.site.register(ReportedViaChoice)
admin.site.register(WatchlistedReport)
admin.site.register(CMSPage)
admin.site.register(BlogPage)
admin.site.register(EvidenceFile, EvidenceFileAdmin)
