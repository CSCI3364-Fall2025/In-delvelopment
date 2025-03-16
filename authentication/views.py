from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView, OAuth2LoginView
from .models import UserProfile

# Create your views here.

def login_view(request):
    # Import models inside the function
    from allauth.socialaccount.models import SocialApp    
    # Ensure OAuth is set up
    try:
        # Check if we have a Google provider
        if not SocialApp.objects.filter(provider='google').exists():
            # If not, try to set it up
            from authentication.apps import AuthenticationConfig
            config = AuthenticationConfig('authentication', 'authentication')
            config.setup_oauth()
    except Exception:
        # If we can't set it up, we'll just continue and let the error happen
        pass
        
    return render(request, 'login.html')

def set_role(request):
    """Store the selected role in session and redirect to Google login"""
    if request.method == 'POST':
        user_role = request.POST.get('user_role', 'student')
        # Store the role in session
        request.session['selected_role'] = user_role
        return redirect('google_login')
    return redirect('login')

def google_login(request):
    # This will be handled by django-allauth
    # Redirect to the allauth Google login URL with proper path
    return redirect('/accounts/google/login/')

@login_required
def logout_view(request):
    return redirect('account_logout')

@login_required
def update_role(request):
    """Update the user's role after successful login"""
    if request.user.is_authenticated:
        selected_role = request.session.get('selected_role', 'student')
        
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.role = selected_role
        user_profile.save()


        if 'selected_role' in request.session:
            del request.session['selected_role']

        # Load progress and store in session
        request.session['progress'] = user_profile.progress_data

        return redirect('dashboard')
    return redirect('login')

def custom_google_callback(request):
    """Custom callback view for Google OAuth"""
    # Force auto-signup
    request.session['socialaccount_auto_signup'] = True
    # Redirect to the standard callback
    return redirect('/accounts/google/login/callback/')

@login_required
def save_progress(request):
    """Save student progress to UserProfile as plain text"""
    if request.method == "POST":
        progress_data = request.POST.get("progress", "")  # Get text-based progress
        
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.progress_data = progress_data  # Store as text
        user_profile.save()
        
        return HttpResponse("Progress saved successfully.")
    
@login_required
def load_progress(request):
    """Retrieve saved progress for the student as plain text"""
    user_profile = UserProfile.objects.get(user=request.user)
    return HttpResponse(user_profile.progress_data)  # Return as plain text