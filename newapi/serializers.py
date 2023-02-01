from rest_framework import serializers
from users.models import *
from .models import *


class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name","last_name","username","email", "phone_number","password")


class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginDetail
        fields = ("username", "password", "mobile_os", "mobile_token")
        extra_kwargs = {'mobile_os': {'required': True}, 'mobile_token': {'required': True}}


class ChangePasswordSerializer(serializers.Serializer):
    model = User
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    model = LoginDetail
    mobile_token = serializers.CharField(required=True)