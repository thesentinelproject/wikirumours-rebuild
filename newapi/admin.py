from django.contrib import admin
from .models import *
# Register your models here.

@admin.register(LoginDetail)
class LoginDetailAdmin(admin.ModelAdmin):
    list_per_page = 7
    search_fields = ('email','mobile_token','mobile_os')
    list_display = ('user','mobile_token','mobile_os')



