from django.contrib.auth.admin import UserAdmin
from django.contrib import admin

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


admin.site.register(User, CustomUserAdmin)
admin.site.register(BlacklistedIP)
