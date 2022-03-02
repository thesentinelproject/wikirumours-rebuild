from django.contrib import admin
from .models import ChatMessage


class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['text','from_user','to_user','created_at','updated_at',]
    search_fields = ['text','from_user__username','to_user__username','created_at','updated_at',]


    class Meta:
        model = ChatMessage

admin.site.register(ChatMessage,ChatMessageAdmin)

