from django.urls import path,include
from . import views
from rest_framework import routers
from .email_confirmation import verify_confirmation
from . import password_reset_views

app_name = "wikirumours_newapi"
router = routers.DefaultRouter()

router.register(r'signup', views.SignUpViewSet)
router.register(r'login', views.LogInViewSet)
router.register(r'changepassword', views.ChangePassword)
router.register(r'logout',views.LogoutViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('activate/<uidb64>/<token>/', verify_confirmation, name='verify_confirmation'),
    path('password_reset/confirm/<token>', password_reset_views.CustomResetPasswordConfirm, name="reset-password-confirm"),
    path('password_reset/', password_reset_views.reset_password_request_token, name="reset-password-request"),
]