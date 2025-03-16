from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from authentication.models import UserProfile

def home(request):
    return render(request, 'home.html')

@login_required
def dashboard(request):
    # Check if user has a profile, create one if not
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)
    
    user_data = {
        'name': request.user.get_full_name() or request.user.username or request.user.email.split('@')[0],
        'email': request.user.email,
        'role': request.user.profile.get_role_display(),
    }
    
    # Add welcome message
    # Add a welcome message to the dashboard (required in delivery 3)
    messages.success(request, f"Welcome {user_data['name']} - {user_data['role']}!")
    
    return render(request, 'dashboard.html', {'user': user_data})
