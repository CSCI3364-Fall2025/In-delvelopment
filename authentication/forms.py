from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from .models import UserProfile


class EmailAuthenticationForm(forms.Form):
    """Simple login form that authenticates users by their email address."""

    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"class": "form-control"}))
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self._user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise forms.ValidationError("Invalid email or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")
            self._user = user

        return cleaned_data

    def get_user(self):
        return self._user


class UserRegistrationForm(forms.Form):
    """Registration form that collects email, password, and role."""

    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"class": "form-control"}))
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )
    role = forms.ChoiceField(
        choices=UserProfile.USER_ROLES,
        widget=forms.RadioSelect,
        initial="student",
        label="I am a",
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if not email.endswith("@bc.edu"):
            raise forms.ValidationError("Please use your Boston College (@bc.edu) email address.")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")

        return cleaned_data

    def save(self):
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        role = self.cleaned_data["role"]

        user = User.objects.create_user(username=email, email=email, password=password)
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()
        return user
