from django.urls import path

from . import views

urlpatterns = [
    path("login", views.login_user, name="login"),
    path("sign_up", views.sign_up, name="sign_up"),
    path("email_sent", views.email_sent, name="email_sent"),
    path(
        "account_verification/<token>",
        views.account_verification,
        name="account_verification",
    ),
    path("reset_password/<token>", views.reset_password, name="reset_password"),
    path("reset_password_post", views.reset_password_post, name="reset_password_post"),
    path("forgot_password", views.forgot_password, name="forgot_password"),
    path("home", views.home_page, name="home"),
    path("logout", views.logout_user, name="logout_user"),
    path("user_profile", views.user_profile, name="user_profile"),
    path("toggle_dark_mode", views.toggle_dark_mode, name="toggle_dark_mode"),
    path("generate_api_key", views.generate_api_key, name="generate_api_key"),
    path("edit_profile", views.edit_profile, name="edit_profile"),
    path("search_user", views.search_user, name="search_user"),
    path("update_profile", views.update_profile, name="update_profile"),
    path("view_user/<username>", views.view_user, name="view_user"),
]
