from django.urls import path

from . import views
from .views import blog_page

urlpatterns = [
    path("", views.index, name="articles"),
    path("content/<content_slug>", blog_page, name="blog_page"),
]
