from django.contrib import admin
from .models  import UserLogs
from django.utils.text import Truncator



class LogsModelAdmin(admin.ModelAdmin):
    def report(self):
        if self.report:
            value = Truncator(self.report.title).words(5)
        else:
            value = None
        return value
    def sighting(self):
        if self.sighting:
            value = Truncator(self.sighting.address).words(5)
        else:
            value = None
        return value
    def comment(self):
        if self.comment:
            value = Truncator(self.comment.comment).words(5)
        else:
            value = None
        return value
    def evidence(self):
        if self.evidence:
            value = Truncator(str(self.evidence.file)).words(5)
        else:
            value = None
        return value
    list_display = ["id","user", "ip_address","action",comment,evidence,report,sighting,"created_at"]
    list_display_links = ["id"]
    extra = 0
    model = UserLogs
    raw_id_fields = ['user','report','sighting']
    date_hierarchy = 'created_at'
    list_filter = ['action','created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__user_name','ip_address','comment__comment','evidence__file','report__title','sighting__address']
    list_per_page = 20
    verbose_name_plural = 'User Logs'
    
admin.site.register(UserLogs, LogsModelAdmin)
