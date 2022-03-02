from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.crypto import get_random_string
from report.models import Domain, Report, Sighting, Comment
from users.models import User, AccountActivationToken
from .emails import account_verification_email, forgot_password_verification, api__key_email
from .forms import LoginForm, SignUpForm, ForgotPasswordForm, EditProfileForm
from django.contrib.sites.shortcuts import get_current_site
from logs.utils import *
from .utils import *


def handler404(request,exception):
    return render(request, 'users/error404.html', status=404)
	


def handler500(request,*args, **argv):
    return render(request, 'users/error500.html', status=500)



def _generate_api_key():
    return get_random_string(12)


def home_page(request):
    return render(request, "report/home.html")


def logout_user(request):
    if request.user.is_authenticated:
        log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Sign Out',}
        create_user_log(log_data)
        logout(request)
        return redirect(reverse("login"))
    return redirect(reverse("login"))


def login_user(request):
    if request.method == "GET":
        if not request.user.is_anonymous:
            return redirect(reverse("home"))
        else:
            form = LoginForm()
            return render(request, "users/login.html", {"form": form})
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = request.POST["username"]
            password = request.POST["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_verified:
                    login(request, user)
                    log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Sign In',}
                    create_user_log(log_data)
                    return redirect(reverse("index"))
                else:
                    account = AccountActivationToken()
                    account.email = user.email
                    account.save()
                    account_verification_email(request, account.token, user.email)
                    return redirect(reverse("email_sent"))
            else:
                check_ip(request)
                messages.error(request, "Invalid username or password")
                return render(request, "users/login.html", {"form": form})
        else:
            return render(request, "users/login.html", {"form": form})


def sign_up(request):
    if request.method == "GET":
        form = SignUpForm()
        return render(request, "users/sign_up.html", {"form": form})
    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            username = request.POST.get("username")
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            email = request.POST.get("email")
            password = request.POST.get("password")
            phone_number = request.POST.get("phone_number")
            request_domain = get_current_site(request).domain
            domain_query = Domain.objects.filter(domain=request_domain)
            if domain_query.exists():
                domain = domain_query.first()
            else:
                domain = Domain.objects.all().first()
            User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                phone_number=phone_number,
                sign_up_domain=domain,
            )
            account = AccountActivationToken()
            account.email = email
            account.save()
            account_verification_email(request, account.token, email)
            return redirect(reverse("email_sent"))
        else:
            check_ip(request)
            return render(request, "users/sign_up.html", {"form": form})


def email_sent(request):
    return render(request, "users/email_sent.html")


def account_verification(request, token=None):
    account = AccountActivationToken.objects.filter(
        token=token, created_at__gte=datetime.now() - timedelta(hours=24)
    ).first()
    if account:
        user = User.objects.filter(email=account.email).first()
        user.is_verified = True
        user.save()
        return redirect(reverse("login"))
    else:
        messages.warning(
            request,
            "The account verification link is invalid or expired. Please log in again.",
        )
        return redirect(reverse("login_user"))


def forgot_password(request):
    if request.method == "GET":
        form = ForgotPasswordForm()
        return render(request, "users/forgot_password.html", {"form": form})
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = request.POST["email"]
            user = User.objects.filter(email=email).first()
            if user:
                account = AccountActivationToken()
                account.email = email
                account.save()
                forgot_password_verification(request, account.token, email)
                return redirect(reverse("email_sent"))
            else:
                check_ip(request)
                form.add_error("email", 'No account exists with that email address')
                return render(request, "users/forgot_password.html", {"form": form})
        else:
            return render(request, "users/forgot_password.html", {"form": form})


def reset_password(request, token=None):
    account = AccountActivationToken.objects.filter(
        token=token, created_at__gte=datetime.now() - timedelta(hours=24)
    ).first()
    if account:

        return render(request, "users/reset_password.html", {"token": token})
    else:
        messages.warning(
            request, "The password reset link is invalid or expired. Please try again."
        )
        return redirect(reverse("login"))


def reset_password_post(request):
    token = request.POST.get("token")
    account_token = AccountActivationToken.objects.filter(
        token=token, created_at__gte=datetime.now() - timedelta(hours=24)
    ).first()
    if not account_token:
        messages.warning(
            request, "The password reset link is invalid or expired. Please try again."
        )
        return redirect(reverse("forgot_password"))
    else:
        user = User.objects.filter(email=account_token.email).first()
        if not user:
            messages.error(request, "User not registered")
            return redirect(reverse("login"))
        else:
            if request.POST.get("password") != request.POST.get("confirm_password"):
                messages.error(request, "Passwords do not match, please try again")
                return redirect(reverse("reset_password", kwargs={"token": token}))
            elif len(request.POST.get("password")) < 8:
                messages.error(
                    request, "Password is too short, please choose a longer password"
                )
                return redirect(reverse("reset_password", kwargs={"token": token}))
            else:
                log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Password Change',}
                create_user_log(log_data)
                user.set_password(request.POST.get("password"))
                user.save()
                messages.success(
                    request, "Your password has been reset. Please log in."
                )
                return redirect(reverse("login"))



@login_required
def generate_api_key(request):
    user = request.user
    user.api_key = _generate_api_key()
    user.save()
    api__key_email(request, user.email)
    log_data = {'ip_address':get_client_ip(request),'user':user,'action':'Generate API Key',}
    create_user_log(log_data)
    return redirect(reverse('user_profile'))



@login_required
def search_user(request):
    if request.method == "GET":
        search_term = request.GET.get('name', None)
        if not search_term:
            return HttpResponseNotAllowed('GET')
        filtered_users = User.objects.filter(Q(first_name__icontains=search_term)
                                             | Q(last_name__icontains=search_term)
                                             | Q(username__icontains=search_term))

        data = []
        for filtered_user in filtered_users:
            data.append({
                "id": filtered_user.username,
                "text": filtered_user.get_full_name,
            })
        response = {"results": data}
        return JsonResponse(data=response, safe=False)
    return HttpResponseNotAllowed('GET')


@login_required
def user_profile(request):
    user = request.user
    context = {"user": user}
    return render(request, "users/user_profile.html", context)


@login_required
def toggle_dark_mode(request):
    user = request.user
    user.is_dark_mode_enabled = not user.is_dark_mode_enabled
    user.save()
    return redirect(reverse('user_profile'))


def view_user(request, username):
    user = get_object_or_404(User, username=username)
    request_domain = get_current_site(request).domain
    domain_query = Domain.objects.filter(domain=request_domain)
    if domain_query.exists():
        domain = domain_query.first()
    else:
        domain = Domain.objects.all().first()
    tab = request.GET.get('tab', None)
    reports = Report.objects.filter(reported_by=user).order_by('-updated_at')
    sightings = Sighting.objects.filter(user=user).order_by('-updated_at')
    comments = Comment.objects.filter(user=user).order_by('-updated_at')
    if not domain.is_root_domain:
        reports = reports.filter(domain=domain)
        sightings = sightings.filter(report__domain=domain)
        comments = comments.filter(report__domain=domain)
    number_of_reports = reports.count()
    number_of_sightings = sightings.count()
    number_of_comments = comments.count()
    context = {
        'user': user,
        'number_of_reports': number_of_reports,
        'number_of_sightings': number_of_sightings,
        'number_of_comments': number_of_comments,
        'tab': tab,
    }
    if tab == 'reports':

        paginator = Paginator(reports, 20)
        page_number = request.GET.get("reports_page")
        page_obj = paginator.get_page(page_number)

        context['reports'] = page_obj.object_list
        context['page_obj'] = page_obj
    elif tab == 'sightings':
        paginator = Paginator(sightings, 20)
        page_number = request.GET.get("sightings_page")
        page_obj = paginator.get_page(page_number)

        context['sightings'] = page_obj.object_list
        context['page_obj'] = page_obj
    elif tab == 'comments':
        paginator = Paginator(comments, 20)
        page_number = request.GET.get("comments_page")
        page_obj = paginator.get_page(page_number)

        context['comments'] = page_obj.object_list
        context['page_obj'] = page_obj
    return render(request, "users/view_user.html", context)


@login_required
def edit_profile(request):
    edit_user_form = EditProfileForm(instance=request.user)
    context = {"user_form": edit_user_form}
    return render(request, "users/edit_profile.html", context)


@login_required
def update_profile(request):
    edit_user_form = EditProfileForm(request.POST, instance=request.user)

    if edit_user_form.is_valid():
        edit_user_form.save()
        log_data = {'ip_address':get_client_ip(request),'user':request.user,'action':'Update User Profile',}
        create_user_log(log_data)
        return redirect(reverse("user_profile"))

    else:
        context = {"user_form": edit_user_form}
        return render(request, "users/edit_profile.html", context)
