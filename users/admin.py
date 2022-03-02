from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django.contrib.auth.models import Group

from .forms import CustomUserCreationForm
from .models import User, BlacklistedIP


# Register your models here.


class CustomUserAdmin(UserAdmin):
    model = User
    add_form = CustomUserCreationForm
    change_form_template = 'loginas/change_form.html'

    # copied from Useradmin and groups and permissions are excluded
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    
        (
            "User Details",
            {
                "fields": (
                    "role",
                    "role_domains",
                    "enable_email_reminders",
                    "enable_email_notifications",
                    "sign_up_domain",
                    "phone_number",
                    "api_key",
                    "api_post_access",
                    "is_verified",
                    "is_user_anonymous",
                    "location",
                    "address",
                    "country",
                )
            },
        ),
    )

    exclude = ['user_permissions']
    list_display = ['username','email','phone_number','first_name','last_name','is_staff','date_joined','sign_up_domain','address','country','role','last_login',]
    search_fields = ['username','first_name','last_name','email','phone_number','sign_up_domain__domain','sign_up_domain__name','api_key','address','country__name','location','role']


class BlacklistedIPAdmin(admin.ModelAdmin):
    list_display = ['id','ip_address','is_whitelisted','created_at']
    list_display_links = ["id"]
    list_filter = ['is_whitelisted','created_at']
    date_hierarchy = 'created_at'
    search_fields = ['ip_address']

admin.site.register(User, CustomUserAdmin)
admin.site.register(BlacklistedIP,BlacklistedIPAdmin)
admin.site.unregister(Group)



