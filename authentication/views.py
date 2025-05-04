from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages #test
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView, OAuth2LoginView
from django.utils import timezone
from assessments.models import Submission
from django.contrib.auth import login
from django.conf import settings

#from authentication.views import login_view #test
from .models import UserProfile, ReportedError


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
    from django.contrib.auth import logout
    
    # Get the user's email before logging them out
    user_email = request.user.email
    
    # Perform the logout
    logout(request)
    
    # Clear any session data
    request.session.flush()
    
    # Check if the email was from BC
    if user_email and not user_email.endswith('@bc.edu'):
        messages.error(request, "Access denied. Only Boston College (@bc.edu) email addresses are allowed.")
    else:
        messages.success(request, "You have been successfully logged out.")
    
    return redirect('home')

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

def login_error(request):
    """Display a user-friendly error page for login issues"""
    error_type = request.GET.get('error', 'unknown')
    email = request.GET.get('email', '')
    
    context = {
        'error_type': error_type,
        'email': email
    }
    
    return render(request, 'login_error.html', context)

def debug_auth(request):
    """Debug view to check authentication status"""
    context = {
        'is_authenticated': request.user.is_authenticated,
        'username': request.user.username if request.user.is_authenticated else None,
        'email': request.user.email if request.user.is_authenticated else None,
        'session_keys': list(request.session.keys()),
    }
    return render(request, 'debug/auth.html', context)

@login_required
def debug_oauth(request):
    """Debug view to check OAuth tokens"""
    from allauth.socialaccount.models import SocialAccount, SocialToken
    
    # Check if user has a Google account
    google_accounts = SocialAccount.objects.filter(user=request.user, provider='google')
    
    if not google_accounts.exists():
        return JsonResponse({
            'has_google_account': False,
            'message': 'No Google account connected'
        })
    
    # Get the Google account
    google_account = google_accounts.first()
    
    # Check if user has a token
    tokens = SocialToken.objects.filter(account=google_account)
    
    if not tokens.exists():
        return JsonResponse({
            'has_google_account': True,
            'has_token': False,
            'message': 'Google account connected but no token found'
        })
    
    # Get the token
    token = tokens.first()
    
    return JsonResponse({
        'has_google_account': True,
        'has_token': True,
        'has_refresh_token': bool(token.token_secret),
        'token_preview': token.token[:10] + '...' if token.token else 'None',
        'refresh_token_preview': token.token_secret[:5] + '...' if token.token_secret else 'None',
        'expires_at': token.expires_at.isoformat() if token.expires_at else None
    })

@login_required
def debug_oauth_flow(request):
    """Debug view to check OAuth flow and force re-authentication"""
    from django.http import JsonResponse
    from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
    from django.shortcuts import redirect
    
    # Check if we're forcing re-auth
    force_reauth = request.GET.get('force', 'false').lower() == 'true'
    
    if force_reauth:
        # Delete existing tokens
        accounts = SocialAccount.objects.filter(user=request.user, provider='google')
        if accounts.exists():
            account = accounts.first()
            tokens = SocialToken.objects.filter(account=account)
            if tokens.exists():
                tokens.delete()
                return JsonResponse({
                    'message': 'Tokens deleted. Please log out and log in again.',
                    'logout_url': '/accounts/logout/',
                    'login_url': '/accounts/google/login/?process=login'
                })
    
    # Get OAuth info
    response_data = {
        'user_email': request.user.email,
        'is_authenticated': request.user.is_authenticated,
    }
    
    # Check if we have a Google SocialApp configured
    try:
        social_app = SocialApp.objects.get(provider='google')
        response_data['social_app'] = {
            'name': social_app.name,
            'client_id': social_app.client_id[:10] + '...',
            'secret': social_app.secret[:5] + '...' if social_app.secret else None,
        }
    except SocialApp.DoesNotExist:
        response_data['social_app'] = 'Not configured'
    
    # Check if user has a Google account
    try:
        social_account = SocialAccount.objects.get(user=request.user, provider='google')
        response_data['social_account'] = {
            'uid': social_account.uid,
            'provider': social_account.provider,
            'last_login': social_account.last_login.isoformat() if social_account.last_login else None,
            'date_joined': social_account.date_joined.isoformat() if social_account.date_joined else None,
        }
    except SocialAccount.DoesNotExist:
        response_data['social_account'] = 'Not found'
    
    # Check if user has a token
    try:
        if 'social_account' in response_data and response_data['social_account'] != 'Not found':
            token = SocialToken.objects.get(account=social_account)
            response_data['social_token'] = {
                'token': token.token[:10] + '...' if token.token else None,
                'token_secret': token.token_secret[:5] + '...' if token.token_secret else None,
                'expires_at': token.expires_at.isoformat() if token.expires_at else None,
            }
    except SocialToken.DoesNotExist:
        response_data['social_token'] = 'Not found'
    
    # Add links for debugging
    response_data['debug_links'] = {
        'force_reauth': request.build_absolute_uri() + '?force=true',
        'test_email': '/assessments/test-email/',
        'logout': '/accounts/logout/',
        'login': '/accounts/google/login/?process=login'
    }
    
    return JsonResponse(response_data)
    
@login_required
def reauth_google(request):
    """View to help users re-authenticate with Google to get fresh tokens"""
    from allauth.socialaccount.models import SocialAccount, SocialToken
    from django.urls import reverse
    
    # Check if user has a Google account
    try:
        social_account = SocialAccount.objects.get(user=request.user, provider='google')
        
        # Check if user already has a token with refresh capability
        has_valid_token = False
        try:
            token = SocialToken.objects.get(account=social_account)
            has_valid_token = bool(token.token_secret)
        except SocialToken.DoesNotExist:
            pass
            
        if has_valid_token:
            messages.info(request, "You already have a valid Google token with refresh capability.")
            return redirect('dashboard')
            
        # Delete any existing tokens to force re-authentication
        SocialToken.objects.filter(account=social_account).delete()
        
        messages.info(request, "Your Google authentication has been reset. Please follow the steps below to reconnect.")
        
    except SocialAccount.DoesNotExist:
        messages.info(request, "You need to connect your Google account to use Gmail features.")
    
    # Add debug information
    debug_info = {
        'user_email': request.user.email,
        'has_google_account': SocialAccount.objects.filter(user=request.user, provider='google').exists(),
    }
    
    if debug_info['has_google_account']:
        social_account = SocialAccount.objects.get(user=request.user, provider='google')
        debug_info['google_uid'] = social_account.uid
        debug_info['has_token'] = SocialToken.objects.filter(account=social_account).exists()
        
        if debug_info['has_token']:
            token = SocialToken.objects.get(account=social_account)
            debug_info['token_preview'] = token.token[:10] + '...' if token.token else None
            debug_info['has_refresh_token'] = bool(token.token_secret)
            debug_info['refresh_token_preview'] = token.token_secret[:5] + '...' if token.token_secret else None
    
    return render(request, 'reauth_google.html', {'debug_info': debug_info})
    
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

# Additional login to create accounts not associated with BC
def test_login(request):
    
    if not settings.DEBUG:
        return redirect('home')

    if request.method == "POST":
        email = request.POST['email']
        role = request.POST['role']
        
        username = email.split('@')[0]
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        
        from .models import UserProfile  
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
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