"""wikirumours URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import HttpResponseRedirect
from django.urls import path, include
from django.conf.urls import url

from django.conf.urls.static import static
from django.conf import settings

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf.urls.i18n import i18n_patterns
from report.views import content_page
from users.views import logout_user
from users.views import handler404,handler500
from rest_framework.routers import DefaultRouter
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet

router = DefaultRouter()
router.register(r'devices', FCMDeviceAuthorizedViewSet)


handler404 = handler404
handler500 = handler500

AdminSite.site_header = 'Settings'
AdminSite.site_title = 'Settings'
AdminSite.index_title = ''



schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = i18n_patterns(
    url(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    url(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    url(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
    # path('api/',include('api.urls')),
    # path('', include(router.urls)),
    path("", lambda r: HttpResponseRedirect("/home")),
    path("admin/", admin.site.urls),
    url(r"^reports/", include("report.urls")),
    url(r"^chat/", include("chat.urls")),
    url(r"^articles/", include("articles.urls")),
    url(r"^api/", include("report.api_urls")),
    url(r"^newapi/", include("newapi.urls")),
    url("", include("users.urls")),
    url(r"^i18n/", include("django.conf.urls.i18n")),
    path("content/<content_slug>", content_page, name="content_page"),

    url(r"^taggit/", include("taggit_selectize.urls")),
    path('', include(router.urls)),
    # path('api/', include('rest_framework.urls')),
)

urlpatterns += path("admin/", include('loginas.urls')),

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
