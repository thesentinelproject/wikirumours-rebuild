from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.forms import TextInput, EmailInput, PasswordInput
from users.models import User
from django.forms import ModelForm
from django import forms
from django.utils.translation import ugettext_lazy
from captcha.fields import ReCaptchaField


class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "shadow  border rounded w-full py-1 md:py-2 mb-3 px-2 md:px-3 text-gray-darker"
            }
        ),
        label=ugettext_lazy("Username"),
        required=True,
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "shadow  border rounded w-full py-1 md:py-2 px-1 md:px-3 text-gray-darker"
            }
        ),
        label=ugettext_lazy("Password"),
        required=True,
    )


class SignUpForm(ModelForm):
    first_name = forms.CharField(
        label=ugettext_lazy("First Name"),
        widget=TextInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )
    last_name = forms.CharField(
        label=ugettext_lazy("Last Name"),
        widget=TextInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )
    username = forms.CharField(
        label=ugettext_lazy("Username"),
        widget=TextInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )
    email = forms.EmailField(
        label=ugettext_lazy("Email"),
        widget=EmailInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )
    phone_number = forms.CharField(
        label=ugettext_lazy("Phone Number"),
        widget=TextInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )
    password = forms.CharField(
        label=ugettext_lazy("Password"),
        validators=[validate_password],
        widget=PasswordInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )
    captcha = ReCaptchaField()


    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "username",
            "email",
            "phone_number",
            "password",
            'captcha',
        )


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label=ugettext_lazy("Email"),
        widget=EmailInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "Email",
            }
        )
    )
    captcha = ReCaptchaField()


# class ResetPasswordForm(forms.Form):
#     password = forms.PasswordInput(
#         attrs={'class': 'shadow  border rounded w-full py-2 px-3 text-grey-darker form-control',
#                'required': 'true',
#                'placeholder': 'Password',
#                'name':'password'
#                }),
#     confirm_password = forms.PasswordInput(
#         attrs={'class': 'shadow  border rounded w-full py-2 px-3 text-grey-darker form-control',
#                'required': 'true',
#                'placeholder': 'Confirm Password',
#                'name':'confirm_password'
#                }),


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = "__all__"


class EditProfileForm(ModelForm):
    first_name = forms.CharField(
        label=ugettext_lazy("First Name"),
        widget=TextInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )
    last_name = forms.CharField(
        label=ugettext_lazy("Last Name"),
        widget=TextInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )
    phone_number = forms.CharField(
        label=ugettext_lazy("Phone Number"),
        widget=TextInput(
            attrs={
                "class": "shadow  border rounded w-full py-2 px-3 text-grey-darker form-control",
                "required": "true",
                "placeholder": "",
            }
        ),
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone_number", "is_user_anonymous")
