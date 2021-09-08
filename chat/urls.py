from django.urls import path

from . import views

urlpatterns = [
    path('', views.chat, name='chat'),
    path('<username>', views.chat, name='chat'),
    path('<username>/send_chat_message/', views.send_chat_message, name='send_chat_message'),
]
