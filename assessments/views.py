from django.shortcuts import render, redirect, get_object_or_404
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
    
    # Example data for assessments
    active_assessments = [
        {'id': 1, 'title': 'Peer Assessment 3', 'course': 'Software Engineering', 'due_date': 'March 21, 11:59 pm'}
    ]
    closed_assessments = [
        {'id': 2, 'title': 'Peer Assessment 1', 'course': 'Software Engineering', 'closed_date': 'February 12, 11:59 pm'},
        {'id': 3, 'title': 'Peer Assessment 2', 'course': 'Software Engineering', 'closed_date': 'February 24, 11:59 pm'}
    ]
    upcoming_assessments = [
        {'id': 4, 'title': 'Peer Assessment 4', 'course': 'Software Engineering', 'open_date': 'April 2, 9:00 am'}
    ]
    
    # Example data for new results notification
    new_results = True  # Set this to True if there are new results to notify the student

    context = {
        'user': user_data,
        'active_assessments': active_assessments,
        'closed_assessments': closed_assessments,
        'upcoming_assessments': upcoming_assessments,
        'num_uncompleted_assessments': len(active_assessments),
        'num_assessment_results': len(closed_assessments),
        'new_results': new_results
    }
    
    # Add welcome message
    messages.success(request, f"Welcome {user_data['name']} - {user_data['role']}!")
    
    return render(request, 'dashboard.html', context)

@login_required
def view_assessment(request, assessment_id):
    # For now, just return a simple response
    return render(request, 'assessment_detail.html', {'assessment_id': assessment_id})