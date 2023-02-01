# from django.contrib import admin
from django.contrib import admin
from mapwidgets import GooglePointFieldWidget
from django.contrib.gis.db import models
from .models import Domain, Report, Sighting, Comment, PriorityChoice, SourceChoice, StatusChoice, ReportedViaChoice, \
    WatchlistedReport, CMSPage, BlogPage, EvidenceFile, NotificationHistoryData
from admin_auto_filters.filters import AutocompleteFilter
from django.utils.text import Truncator


class DomainAdmin(admin.ModelAdmin):
    list_display = ['name','domain','is_root_domain','index_cms_page']
    search_fields = ['name','domain','is_root_domain','index_cms_page__title']
    model = Domain


def location_coords(self):
    if self.location:
        value = tuple(reversed(self.location.coords))
    else:
        value = None
    return value
location_coords.admin_order_field = 'location'




class ReportAdmin(admin.ModelAdmin):
    model = Report
    list_display = ['public_id','title', 'domain',location_coords, 'country', 'priority', 'status', 'reported_by','recently_edited_by','occurred_on','created_at']
    search_fields = ['title','public_id','reported_by__first_name','reported_by__last_name','reported_by__username','country__name','status__name','address','domain__domain','recently_edited_by__username','occurred_on','created_at','updated_at']
    formfield_overrides = {models.PointField: {"widget": GooglePointFieldWidget}}


class ReportFilter(AutocompleteFilter):
    title = 'Report'
    field_name = 'report'


class SightingAdmin(admin.ModelAdmin):
    def report(self):
        return Truncator(self.report.title).words(5)
    model = Sighting
    list_filter = [ReportFilter]
    list_display = [report, 'country', 'user',location_coords,'heard_on','created_at','updated_at']
    search_fields = ['user__username','user__first_name','user__last_name','report__title','date','source__name','reported_via__name','overheard_at__name','country__name','address','heard_on','created_at','updated_at']
    formfield_overrides = {models.PointField: {"widget": GooglePointFieldWidget}}




class StatusChoiceAdmin(admin.ModelAdmin):
    model = StatusChoice
    search_fields = ['name','sequence_number','icon']
    list_display = ['name', 'sequence_number','icon']



class CommentsAdmin(admin.ModelAdmin):
    def report(self):
        return Truncator(self.report.title).words(10)
    def comment(self):
        return Truncator(self.comment).words(5)
    list_display = ['user',report,comment,'created_at','updated_at']
    search_fields = ['user__username','user__first_name','user__last_name','report__title','comment','created_at','updated_at']
    model = Comment



class EvidenceFileAdmin(admin.ModelAdmin):
    model = EvidenceFile
    list_filter = [ReportFilter,'created_at']
    search_fields = ['report__title','uploader__username','is_public','file']
    list_display = ['uploader','file', 'is_public', 'report', 'created_at',]



class PriorityChoiceAdmin(admin.ModelAdmin):
    list_display = ['name','sequence_number','number_of_days_before_alert','colour','icon']
    search_fields = ['name','sequence_number','number_of_days_before_alert','colour','icon']
    model = PriorityChoice


class SourceChoiceAdmin(admin.ModelAdmin):
    list_display = ['name',]
    search_fields = ['name',]
    model = SourceChoice 

class ReportedViaChoiceAdmin(admin.ModelAdmin):
    search_fields = ['name',]
    list_display = ['name',]
    model = ReportedViaChoice 

class WatchlistedReportAdmin(admin.ModelAdmin):
    list_display = ['user','report','created_at','updated_at',]
    search_fields = ['user__username','user__first_name','user__last_name','report__title','created_at','updated_at',]
    model = WatchlistedReport 


class CMSPageAdmin(admin.ModelAdmin):
    list_display = ['title','internal_title','content_slug','sequence_number','created_at','updated_at',]
    search_fields = ['title','internal_title','content_slug','sequence_number','created_at','updated_at',]
    model = CMSPage 


class BlogPageAdmin(admin.ModelAdmin):
    list_display = ['title','internal_title','content_slug','sequence_number','created_at','updated_at',]
    search_fields = ['title','internal_title','content_slug','sequence_number','created_at','updated_at',]
    model = BlogPage 


class NotificationAdmin(admin.ModelAdmin):
    list_per_page = 7
    search_fields = ('user','text','title','time')
    list_display = ('user','text','title','time')


admin.site.register(Domain, DomainAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(Sighting, SightingAdmin)
admin.site.register(Comment, CommentsAdmin)
admin.site.register(StatusChoice, StatusChoiceAdmin)
admin.site.register(EvidenceFile, EvidenceFileAdmin)
admin.site.register(PriorityChoice,PriorityChoiceAdmin)
admin.site.register(SourceChoice,SourceChoiceAdmin)
admin.site.register(ReportedViaChoice,ReportedViaChoiceAdmin)
admin.site.register(WatchlistedReport,WatchlistedReportAdmin)
admin.site.register(CMSPage,CMSPageAdmin)
admin.site.register(BlogPage,BlogPageAdmin)
admin.site.register(NotificationHistoryData,NotificationAdmin)




