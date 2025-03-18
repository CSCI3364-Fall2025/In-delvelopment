from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from authentication.models import UserProfile, AssessmentProgress
from .models import Assessment, AssessmentSubmission  # Import the Assessment and AssessmentSubmission models
from .models import Assessment, AssessmentSubmission

def home(request):
    return render(request, 'home.html')

def dashboard(request):
    # Check if user is authenticated
    if not request.user.is_authenticated:
        # Redirect to our custom login page instead of the default login page
        return render(request, 'please_login.html')
    
    # Check if user has a BC email
    if not request.user.email.endswith('@bc.edu'):
        from django.contrib.auth import logout
        logout(request)
        messages.error(request, "Access denied. Only Boston College (@bc.edu) email addresses are allowed.")
        return redirect('home')
    
    # Check if user has a profile, create one if not
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)
    
    user_data = {
        'name': request.user.get_full_name() or request.user.username or request.user.email.split('@')[0],
        'email': request.user.email,
        'role': request.user.profile.get_role_display(),
    }
    
    # Get or create assessments
    assessment1, _ = Assessment.objects.get_or_create(
        id=1, 
        defaults={
            'title': 'Peer Assessment 3', 
            'course': 'Software Engineering', 
            'due_date': '2025-03-21 23:59:00'
        }
    )
    assessment2, _ = Assessment.objects.get_or_create(
        id=2, 
        defaults={
            'title': 'Peer Assessment 1', 
            'course': 'Software Engineering', 
            'closed_date': '2025-02-12 23:59:00'
        }
    )
    assessment3, _ = Assessment.objects.get_or_create(
        id=3, 
        defaults={
            'title': 'Peer Assessment 2', 
            'course': 'Software Engineering', 
            'closed_date': '2025-02-24 23:59:00'
        }
    )
    assessment4, _ = Assessment.objects.get_or_create(
        id=4, 
        defaults={
            'title': 'Peer Assessment 4', 
            'course': 'Software Engineering', 
            'open_date': '2025-04-02 09:00:00'
        }
    )
    
    # Get or create submissions
    AssessmentSubmission.objects.get_or_create(
        assessment=assessment2,
        student='Julian Castro',
        defaults={
            'contribution': 4,
            'teamwork': 4,
            'communication': 4,
            'feedback': 'Great job on the project!'
        }
    )
    AssessmentSubmission.objects.get_or_create(
        assessment=assessment2,
        student='Alice',
        defaults={
            'contribution': 3,
            'teamwork': 3,
            'communication': 3,
            'feedback': 'Needs improvement in communication.'
        }
    )
    AssessmentSubmission.objects.get_or_create(
        assessment=assessment2,
        student='Bob',
        defaults={
            'contribution': 5,
            'teamwork': 5,
            'communication': 5,
            'feedback': 'Excellent teamwork and contribution.'
        }
    )
    AssessmentSubmission.objects.get_or_create(
        assessment=assessment2,
        student='Charlie',
        defaults={
            'contribution': 2,
            'teamwork': 2,
            'communication': 2,
            'feedback': 'Average performance overall.'
        }
    )
    AssessmentSubmission.objects.get_or_create(
        assessment=assessment3,
        student='Julian Castro',
        defaults={
            'contribution': 4,
            'teamwork': 4,
            'communication': 4,
            'feedback': 'Great job on the project!'
        }
    )
    AssessmentSubmission.objects.get_or_create(
        assessment=assessment3,
        student='Alice',
        defaults={
            'contribution': 3,
            'teamwork': 3,
            'communication': 3,
            'feedback': 'Needs improvement in communication.'
        }
    )
    AssessmentSubmission.objects.get_or_create(
        assessment=assessment3,
        student='Bob',
        defaults={
            'contribution': 5,
            'teamwork': 5,
            'communication': 5,
            'feedback': 'Excellent teamwork and contribution.'
        }
    )
    AssessmentSubmission.objects.get_or_create(
        assessment=assessment3,
        student='Charlie',
        defaults={
            'contribution': 2,
            'teamwork': 2,
            'communication': 2,
            'feedback': 'Average performance overall.'
        }
    )
    
    active_assessments = [
        {'id': 1, 'title': 'Peer Assessment 3', 'course': 'Software Engineering', 'due_date': '2025-03-21', 'due_time': '23:59:00'}
    ]
    closed_assessments = [
        {'id': 2, 'title': 'Peer Assessment 1', 'course': 'Software Engineering', 'closed_date': '2025-02-12', 'closed_time': '23:59:00', 'grade': 'A'},
        {'id': 3, 'title': 'Peer Assessment 2', 'course': 'Software Engineering', 'closed_date': '2025-02-24', 'closed_time': '23:59:00', 'grade': 'B+'}
    ]
    upcoming_assessments = [
        {'id': 4, 'title': 'Peer Assessment 4', 'course': 'Software Engineering', 'open_date': '2025-04-02', 'open_time': '09:00:00'}
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
        'new_results': new_results,
        'request': request,
    }
    
    # Add welcome message
    messages.success(request, f"Welcome {user_data['name']} - {user_data['role']}!")
    
    return render(request, 'dashboard.html', context)

@login_required
def view_assessment(request, assessment_id):
    # Fetch the assessment details from the database
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Fetch the comments for the professor view
    comments = AssessmentSubmission.objects.filter(assessment=assessment).values_list('feedback', flat=True)
    
    progress, created = AssessmentProgress.objects.get_or_create(
        student=request.user,
        assessment=assessment,
    )

    context = {
        'assessment': assessment,
        'comments': comments, 
        'progress': progress,
    }
    
    return render(request, 'assessment_detail.html', context)

@login_required
def save_progress(request, assessment_id):
    """Save student's progress."""
    if request.method == "POST":
        progress_notes = request.POST.get("progress", "").strip()
        assessment = get_object_or_404(Assessment, id=assessment_id)

        # Retrieve or create a progress entry for the user
        progress, _ = AssessmentProgress.objects.get_or_create(
            student=request.user, assessment=assessment
        )
        progress.progress_notes = progress_notes  # Save progress text
        progress.save()

        messages.success(request, "Your progress has been saved successfully.")
        return redirect('view_assessment', assessment_id=assessment_id)


@login_required
def submit_assessment(request, assessment_id):
    if request.method == 'POST':
        assessment = get_object_or_404(Assessment, id=assessment_id)
        student = request.POST['student']
        contribution = request.POST['contribution']
        teamwork = request.POST['teamwork']
        communication = request.POST['communication']
        feedback = request.POST['feedback']
        
        # Save the assessment submission
        AssessmentSubmission.objects.create(
            assessment=assessment,
            student=student,
            contribution=contribution,
            teamwork=teamwork,
            communication=communication,
            feedback=feedback
        )
        
        messages.success(request, 'Assessment submitted successfully.')
        return redirect('view_assessment', assessment_id=assessment_id)
    
    return redirect('dashboard')

@login_required
def view_all_published_results(request):
    # Example data for published results
    published_results = [
        {'id': 2, 'title': 'Peer Assessment 1', 'course': 'Software Engineering', 'closed_date': '2025-02-12', 'closed_time': '23:59:00', 'grade': 'A'},
        {'id': 3, 'title': 'Peer Assessment 2', 'course': 'Software Engineering', 'closed_date': '2025-02-24', 'closed_time': '23:59:00', 'grade': 'B+'}
    ]
    
    context = {
        'published_results': published_results
    }
    
    return render(request, 'published_results.html', context)

@login_required
def view_comments(request, assessment_id):
    # Fetch the assessment details from the database
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Example comments data
    comments = [
        ('Julian Castro', 'Great job on the project!'),
        ('Alice', 'Needs improvement in communication.'),
        ('Bob', 'Excellent teamwork and contribution.'),
        ('Charlie', 'Average performance overall.')
    ]
    
    context = {
        'assessment': assessment,
        'comments': comments
    }
    
    return render(request, 'comments.html', context)

@login_required
def edit_profile(request, name):
    
    user_data = {
        'name': request.user.get_full_name() or request.user.username or request.user.email.split('@')[0],
        'email': request.user.email,
        'role': request.user.profile.get_role_display(),
    }

    return render(request, 'edit_profile.html', {
        "user": user_data
    })