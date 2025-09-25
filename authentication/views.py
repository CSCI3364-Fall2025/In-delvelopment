from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

from assessments.models import Submission

from .forms import EmailAuthenticationForm, UserRegistrationForm
from .models import UserProfile, ReportedError


def login_view(request):
    """Render and process the email/password login form."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = EmailAuthenticationForm(request=request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)

        # Mirror the user's role in the session for downstream checks
        if hasattr(user, 'profile'):
            request.session['selected_role'] = user.profile.role
            request.session['user_role'] = user.profile.role
        else:
            request.session['selected_role'] = 'student'
            request.session['user_role'] = 'student'

        messages.success(request, "Welcome back!")
        return redirect('dashboard')

    return render(request, 'login.html', {'form': form})


def signup_view(request):
    """Allow a new user to create an account with an email and password."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = UserRegistrationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        request.session['selected_role'] = user.profile.role
        request.session['user_role'] = user.profile.role
        messages.success(request, "Your account has been created. Welcome!")
        return redirect('dashboard')

    return render(request, 'signup.html', {'form': form})


@login_required
def logout_view(request):
    """Log out the current user and clear session data."""
    user_email = request.user.email
    logout(request)
    request.session.flush()

    if user_email and not user_email.endswith('@bc.edu'):
        messages.error(request, "Access denied. Only Boston College (@bc.edu) email addresses are allowed.")
    else:
        messages.success(request, "You have been successfully logged out.")

    return redirect('home')


@login_required
def save_progress(request):
    """Save student progress to UserProfile as plain text."""
    if request.method == "POST":
        progress_data = request.POST.get("progress", "")

        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.progress_data = progress_data
        user_profile.save()

        return HttpResponse("Progress saved successfully.")


@login_required
def load_progress(request):
    """Retrieve saved progress for the student as plain text."""
    user_profile = UserProfile.objects.get(user=request.user)
    return HttpResponse(user_profile.progress_data)


def login_error(request):
    """Display a user-friendly error page for login issues."""
    error_type = request.GET.get('error', 'unknown')
    email = request.GET.get('email', '')

    context = {
        'error_type': error_type,
        'email': email
    }

    return render(request, 'login_error.html', context)


def debug_auth(request):
    """Debug view to check authentication status."""
    context = {
        'is_authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
        'email': request.user.email if request.user.is_authenticated else None,
        'session_keys': list(request.session.keys()),
    }
    return render(request, 'debug/auth.html', context)


def verify_submission(request):
    token = request.GET.get("token")
    try:
        sub = Submission.objects.get(verification_token=token)
    except Submission.DoesNotExist:
        messages.error(request, "Invalid verification link.")
        return redirect("home")

    if sub.token_expires_at < timezone.now():
        messages.error(request, "This link has expired.")
        return redirect("home")

    sub.mark_verified()
    messages.success(request, "Your submission has been verified!")
    return redirect("submission_detail", pk=sub.pk)


def test_login(request):
    """Simple debug login flow available when DEBUG is True."""
    if not settings.DEBUG:
        return redirect('home')

    if request.method == "POST":
        email = request.POST['email']
        role = request.POST['role']

        username = email
        user, _ = User.objects.get_or_create(username=username, defaults={'email': email})

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        request.session['selected_role'] = profile.role
        request.session['user_role'] = profile.role
        return redirect('dashboard')

    return render(request, 'debug/test_login.html')


@login_required
def report_issue(request):
    if request.method == "POST":
        user = request.user
        error = request.POST.get('issue')

        ReportedError.objects.create(user=user, error=error)
        messages.success(request, "Thank you! Your issue has been submitted to the admin team.")
        return redirect('dashboard')

    return render(request, 'report_issue.html')
