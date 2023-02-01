from django.shortcuts import render, redirect
from rest_framework.response import Response
from rest_framework import viewsets
from django.contrib.auth import authenticate, login
from django.contrib.sites.shortcuts import get_current_site
from rest_framework.decorators import action, api_view
import json
import os
from .email_confirmation import send_confirmation_mail
from django.db.models import Q, Count
from django.urls import reverse_lazy
from rest_framework.pagination import PageNumberPagination, _positive_int
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .serializers import *
from users.models import *
from .models import *
from django.conf import settings
from django.contrib import messages
from rest_framework import filters
from rest_framework import generics
from rest_framework.views import APIView
from django.db.models import Avg
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.decorators import api_view, renderer_classes
from .jwt_token_auth import get_token, decrypt_token
from report.send_notification import FCMPushView, add_mobile_token, delete_mobile_token, update_mobile_token
from fcm_django.models import FCMDevice

class SignUpViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = SignupSerializer
    http_method_names = ['post']

    def list(self, request):
        return Response({"status": 0, "message": "User Listing is not allowed"})

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            first_name = request.data['first_name']
            last_name = request.data['last_name']
            username = request.data['username']
            email = request.data['email']
            phone_number = request.data['phone_number']
            password = request.data['password']
            
            
            # mobile_number = request.data['mobile_number'] if request.data.get('mobile_number') else None
            user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name,
                                            phone_number=phone_number, is_active=True)
            email_sent_status = send_confirmation_mail(request, user, email)
            if email_sent_status:
                return Response(
                    {"status": 1, "message": "Please confirm your email address to complete the registration"})
            return Response({"status": 1, "message": "Acoount successfully created.", "data": serializer.data})
        if "first_name" in serializer.errors:
            return Response({"status": 0, "message": "first_name - " + serializer.errors['first_name'][0]})
        if "last_name" in serializer.errors:
            return Response({"status": 0, "message": "last_name - " + serializer.errors['last_name'][0]})
        if "username" in serializer.errors:
            return Response({"status": 0, "message": "username - " + serializer.errors['username'][0]})
        if "email" in serializer.errors:
            if serializer.errors['email'][0] == "user with this email address already exists.":
                return Response({"status": 0, "message": "Email is already registered"})
            return Response({"status": 0, "message": "email - " + serializer.errors['email'][0]})
        if "password" in serializer.errors:
            return Response({"status": 0, "message": "passowrd - " + serializer.errors['password'][0]})
        if "phone_number" in serializer.errors:
            return Response({"status": 0, "message": "phone_number - " + serializer.errors['phone_number'][0]})
        return Response(serializer.errors)


class LogInViewSet(viewsets.ModelViewSet):
    queryset = LoginDetail.objects.all()
    serializer_class = LoginSerializer
    http_method_names = ['post']

    def get_user(self, username):
        try:
            user = User.objects.get(username=username)
            return user
        except:
            return 0

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        current_site = get_current_site(request)
        if serializer.is_valid():
            username = request.data['username']
            password = request.data['password']
            mobile_os = request.data['mobile_os']
            mobile_token = request.data['mobile_token']
            user = self.get_user(username)
            if user:
                if user.is_active and user.is_verified:
                    auth_status = authenticate(username=username, password=password)
                    print(auth_status)
                    if auth_status:
                        token = get_token(user)
                         
                        
                        try:
                            logindetail = LoginDetail.objects.filter(user=user)
                            for device in logindetail:
                                device.delete()
                            LoginDetail.objects.create(user=user, username=username, mobile_os=mobile_os,
                                                       mobile_token=mobile_token)
                        except:
                            LoginDetail.objects.create(user=user, username=username, mobile_os=mobile_os,
                                                       mobile_token=mobile_token)
                        # LoginDetail.objects.create(user=user,email=email,mobile_os=mobile_os,mobile_token=mobile_token)
                        role_domains_data = []
                        for obj in user.role_domains.all():
                            role_domains_data.append({"domain_id":obj.id, "domain_name":obj.name,"domain_role":user.role})
                        data = {"user_id":user.id,"username": user.username,"first_name": user.first_name,
                                "last_name": user.last_name, "email": user.email, "phone_number": user.phone_number,
                                "token": token['access_token'], "role": user.role,"role_domains":role_domains_data
                                }
                        fcm_obj = FCMDevice.objects.filter(user=user)
                        if fcm_obj:
                            for obj in fcm_obj:
                                obj.delete()
                        FCMDevice.objects.create(registration_id=mobile_token,type="android",user=user)
                        # add_mobile_token(user, mobile_os, mobile_token)
                        return Response({"status": 1, "message": "You have logged in successfully", "data": data})
                    else:
                        return Response({"status": 0, "message": "Unable to log in, please check your password"})
                else:
                    return Response({"status": 0, "message": "Please verify the link sent to your email to log in"})
            else:
                return Response({"status": 0, "message": "Username is not registered"})

        if "username" in serializer.errors:
            return Response({"status": 0, "message": "username - " + serializer.errors['username'][0]})
        if "password" in serializer.errors:
            return Response({"status": 0, "message": "password - " + serializer.errors['password'][0]})
        if "mobile_os" in serializer.errors:
            return Response({"status": 0, "message": "mobile_os - " + serializer.errors['mobile_os'][0]})
        if "mobile_token" in serializer.errors:
            return Response({"status": 0, "message": "mobile_token - " + serializer.errors['mobile_token'][0]})
        return Response(serializer.errors)


class ChangePassword(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = ChangePasswordSerializer
    http_method_names = ['post']

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            old_password = request.data['old_password']
            new_password = request.data['new_password']
            token = request.META.get("HTTP_AUTHORIZATION")
            user = decrypt_token(token)
            if user:
                # auth_status = authenticate(email=user.email,password=old_password)
                auth_status = authenticate(username=user.username, password=old_password)
                if auth_status:
                    user.set_password(new_password)
                    user.save()
                    return Response({"status": 1, "message": "password changed successfully"})
                else:
                    return Response({"status": 0, "message": "Please enter correct old password"})
            else:
                return Response({"status": 3, "message": "invalid access token"})
        if "old_password" in serializer.errors:
            return Response({"status": 0, "message": "old-password - " + serializer.errors['old_password'][0]})
        if "new_password" in serializer.errors:
            return Response({"status": 0, "message": "new-password - " + serializer.errors['new_password'][0]})
        return Response(serializer.errors)



class LogoutViewSet(viewsets.ModelViewSet):
    queryset = LoginDetail.objects.all()
    serializer_class = LogoutSerializer
    http_method_names = ['post']

    def validate_mobile_token(self, user, mobile_token):
        try:
            logged_in_user = LoginDetail.objects.filter(user=user)
            return logged_in_user
        except:
            return 0

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            mobile_token = request.data['mobile_token'] if request.data.get('mobile_token') else None
            token = request.META.get("HTTP_AUTHORIZATION")
            user = decrypt_token(token)
            if user:
                logged_in_user = self.validate_mobile_token(user, mobile_token)
                if logged_in_user:
                    for item in logged_in_user:
                        item.delete()
                    fcm_obj = FCMDevice.objects.filter(user=user)
                    if fcm_obj:
                        for obj in fcm_obj:
                            obj.delete()
                    # delete_mobile_token(user,mobile_token)

                    # logged_in_user.delete()
                    return Response({"status": 1, "message": "Logged out successfully"})
                else:
                    return Response({"status": 1, "message": "Invalid mobile token"})
            else:
                return Response({"status": 1, "message": "Logged out successfully"})
        if "mobile_token" in serializer.errors:
            return Response({"status": 1, "message": "mobile-token - " + serializer.errors['mobile_token'][0]})
        return Response(serializer.errors)




