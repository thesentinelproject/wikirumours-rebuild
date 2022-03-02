from django.contrib import admin
from .models import Country


class CountryAdmin(admin.ModelAdmin):
    list_display = ['name','iso_code',]
    search_fields = ['name','iso_code',]


    class Meta:
        model = Country

admin.site.register(Country,CountryAdmin)