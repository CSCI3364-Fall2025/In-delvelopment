from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from authentication.models import UserProfile, AssessmentProgress
from .models import Assessment, AssessmentSubmission  # Import the Assessment and AssessmentSubmission models
from .models import Assessment, AssessmentSubmission

from django.shortcuts import HttpResponse #imports for scheduler
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from assessments.models import Assessment, Course, Team 
from django.contrib.auth.models import User

#imports for averages
from django.http import JsonResponse
from django.db.models import Avg
from assessments.models import Assessment, AssessmentScore
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings

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

    # Get current user profile
    current_user = UserProfile.objects.get(user=request.user)
    
    # Synchronize session with profile role
    request.session['selected_role'] = current_user.role
    request.session['user_role'] = current_user.role
    
    # Check if the user has updated their profile 
    if request.method == "POST":
        selected_role = request.POST['edit_role']
        preferred_name = request.POST['preferred_name']

        current_user.role = selected_role
        current_user.preferred_name = preferred_name
        current_user.save()
        
        # Update session to match profile role
        request.session['selected_role'] = selected_role
        request.session['user_role'] = selected_role
        
        messages.success(request, 'Your profile has been successfully updated.')
    
    user_data = {
        'preferred_name': current_user.preferred_name if current_user.preferred_name != None else (request.user.get_full_name() or request.user.username or request.user.email.split('@')[0]),
        'real_name': request.user.get_full_name() or request.user.username or request.user.email.split('@')[0], 
        'email': request.user.email,
        'role': current_user.role,
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
        'active_courses': request.user.courses.filter(is_active=True) | request.user.created_courses.filter(is_active=True)
    }
    
    # Add welcome message
    messages.success(request, f"Welcome {user_data['preferred_name']} - {user_data['role']}!")
    
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
        return redirect('dashboard')
   
@login_required
def load_progress(request, assessment_id):
    """Retrieve saved progress for the student for a specific assessment."""
    assessment = get_object_or_404(Assessment, id=assessment_id)

    # Try to get the user's progress for the specific assessment
    progress = AssessmentProgress.objects.filter(student=request.user, assessment=assessment).first()

    if progress:
        # If progress exists, pass the progress data to the template
        feedback = progress.progress_notes
    else:
        # If no progress exists, set progress_notes to an empty string or a placeholder
        progress_notes = ""

    # Pass the progress data to the context and render the assessment detail page
    context = {
        'assessment': assessment,
        'progress_notes': progress_notes,
    }

    return render(request, 'assessment_detail.html', context)


@login_required
def submit_assessment(request, assessment_id):
    if request.method == 'POST':
        assessment = get_object_or_404(Assessment, id=assessment_id)
        student = request.POST['student']
        contribution = request.POST['contribution']
        teamwork = request.POST['teamwork']
        communication = request.POST['communication']

        # Retrieve the student's saved progress (if any)
        progress = AssessmentProgress.objects.filter(student=request.user, assessment=assessment).first()
        feedback = progress.progress_notes if progress else ""  # Use saved progress notes as feedback
        
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
    current_user = UserProfile.objects.get(user=request.user)

    if request.method == "POST":
        selected_role = request.POST.get('edit_role')
        preferred_name = request.POST.get('preferred_name')

        current_user.role = selected_role
        current_user.preferred_name = preferred_name
        current_user.save()
        
        # Update session to match profile role
        request.session['selected_role'] = selected_role
        request.session['user_role'] = selected_role
        
        messages.success(request, 'Your profile has been successfully updated.')
        return redirect('dashboard')

    user_data = {
        'preferred_name': current_user.preferred_name if current_user.preferred_name != None else (request.user.get_full_name() or request.user.username or request.user.email.split('@')[0]),
        'real_name': request.user.get_full_name() or request.user.username or request.user.email.split('@')[0], 
        'email': request.user.email,
        'role': current_user.role,
    }

    return render(request, 'edit_profile.html', {
        "user": user_data
    })
    

def send_deadline_notifications_view(request):
    upcoming_deadline = timezone.now() + timedelta(days=3)
    
    assessments = Assessment.objects.filter(due_date__date=upcoming_deadline.date())  # FIXED

    if not assessments.exists():
        return HttpResponse("No assessments due in 3 days.")

    emails_sent = 0

    for assessment in assessments:
        students = assessment.students.all()

        for student in students:
            if not student.email:
                continue

            subject = "Reminder: Assessment Deadline Approaching"
            message = (
                f"Dear {student.username},\n\n"
                f"This is a reminder that your assessment '{assessment.title}' is due on {assessment.due_date.strftime('%Y-%m-%d %H:%M')}. "
                "Please make sure to submit it on time.\n\n"
                "Best regards,\nYour Course Team"
            )

            send_mail(subject, message, settings.EMAIL_HOST_USER, [student.email])
            emails_sent += 1

    return HttpResponse(f"Deadline notification emails sent successfully. {emails_sent} emails delivered.")

#average score functionality
@login_required
def student_average_score(request):
    """Returns the average score of the logged-in student."""
    student = request.user
    scores = AssessmentScore.objects.filter(student=student)

    if not scores.exists():
        return JsonResponse({"student": student.username, "average_score": "No scores available"}, status=200)

    average = scores.aggregate(Avg("score"))["score__avg"]
    return JsonResponse({"student": student.username, "average_score": round(average, 2)})

@login_required
def professor_average_scores(request):
    """Returns the average score for each assessment."""
    assessments = Assessment.objects.prefetch_related("scores").all()
    results = []

    for assessment in assessments:
        average = assessment.scores.aggregate(Avg("score"))["score__avg"]
        results.append({
            "assessment": assessment.title,
            "average_score": round(average, 2) if average else "No scores"
        })

    return JsonResponse(results, safe=False)

@login_required
def course_dashboard(request):

    current_user = UserProfile.objects.get(user=request.user)
    
    user_data = {
        'preferred_name': current_user.preferred_name if current_user.preferred_name != None  else (request.user.get_full_name() or request.user.username or request.user.email.split('@')[0]),
        'real_name': request.user.get_full_name() or request.user.username or request.user.email.split('@')[0], 
        'email': request.user.email,
        'role': current_user.role,
    }

    #check if a new course has been created
    if request.method == "POST":
        new_course = Course.objects.create(
            name=request.POST['courseName'],
            course_code=request.POST['courseCode'],
            year=request.POST['year'],
            semester=request.POST['semester'],
            description=request.POST['description'],
            created_by = request.user,
        )
        num_teams = request.POST['numTeams']
        for i in range(int(num_teams)):
            new_team = Team.objects.create()
            new_team.save()
            new_course.teams.add(new_team)
        new_course.save()
        messages.success(request, f"Successfully created course '{new_course.name}'")   

    return render(request, 'course_dashboard.html', {
        "user": user_data, "courses": request.user.courses.filter(is_active=True) | request.user.created_courses.filter(is_active=True),
        "closed_courses": request.user.courses.filter(is_active=False)
    })

@login_required
def create_course(request):
    return render(request, 'create_course.html')

@login_required
def view_course(request, course_name):

    course = Course.objects.get(name=course_name)

    return render(request, 'view_course.html', {
        "course": course, "teams": course.teams.all(),
        "assessments": course.assessments.all()
    })

@login_required
def invite_students(request):
    """Send invitation emails to students to join the system."""
    # Check if user is a professor
    is_professor = (
        hasattr(request.user, 'profile') and request.user.profile.role == 'professor'
    ) or request.session.get('user_role') == 'professor'
    
    if not is_professor:
        messages.error(request, "Only professors can invite students.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Get email addresses from the form
        email_list = request.POST.get('student_emails', '').strip().split('\n')
        email_list = [email.strip() for email in email_list if email.strip()]
        
        # Validate emails
        valid_emails = []
        invalid_emails = []
        
        for email in email_list:
            try:
                validate_email(email)
                # Check if it's a BC email
                if not email.endswith('@bc.edu'):
                    invalid_emails.append(f"{email} (not a BC email)")
                else:
                    valid_emails.append(email)
            except ValidationError:
                invalid_emails.append(f"{email} (invalid format)")
        
        # Send invitations to valid emails
        if valid_emails:
            course_name = request.POST.get('course_name', 'the course')
            emails_sent = 0
            
            for email in valid_emails:
                subject = "Invitation to Boston College Peer Assessment System"
                message = (
                    f"Dear Student,\n\n"
                    f"You have been invited by Professor {request.user.get_full_name() or request.user.username} "
                    f"to join the Boston College Peer Assessment System for {course_name}.\n\n"
                    f"Please visit {request.build_absolute_uri('/login/')} to log in with your BC credentials.\n\n"
                    "Best regards,\nPeer Assessment System"
                )
                
                try:
                    send_mail(
                        subject, 
                        message, 
                        settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com',
                        [email]
                    )
                    emails_sent += 1
                except Exception as e:
                    messages.error(request, f"Error sending to {email}: {str(e)}")
            
            if emails_sent > 0:
                messages.success(request, f"Successfully sent {emails_sent} invitation(s).")
            
        # Report invalid emails
        if invalid_emails:
            messages.warning(request, f"Could not send to the following emails: {', '.join(invalid_emails)}")
            
        return redirect('invite_students')
    
    # For GET requests, just show the form
    return render(request, 'invite_students.html')

def test_email(request):
    """Send a test email to verify email configuration"""
    if not request.user.is_authenticated:
        return HttpResponse("Please log in first")
    
    try:
        send_mail(
            'Test Email from Peer Assessment System',
            f'This is a test email sent to {request.user.email}.\n\nIf you received this, your email configuration is working!',
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
        return HttpResponse(f"Test email sent to {request.user.email}. Check your console output or email inbox depending on your backend configuration.")
    except Exception as e:
        return HttpResponse(f"Error sending email: {str(e)}")
    
def debug_user_role(request):
    """Debug view to check user role"""
    if not request.user.is_authenticated:
        return HttpResponse("Not logged in")
    
    output = f"Username: {request.user.username}<br>"
    output += f"Email: {request.user.email}<br>"
    
    if hasattr(request.user, 'profile'):
        output += f"Profile role: {request.user.profile.role}<br>"
    else:
        output += "No profile found<br>"
    
    # Check session
    output += f"<br>Session data:<br>"
    for key, value in request.session.items():
        output += f"{key}: {value}<br>"
    
    return HttpResponse(output)

@login_required
def fix_session_role(request):
    """Fix the session role to match the profile role"""
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)
    
    profile = request.user.profile
    
    # Update session to match profile
    request.session['selected_role'] = profile.role
    request.session['user_role'] = profile.role
    
    messages.success(request, f"Session role updated to match profile role: {profile.role}")
    return redirect('dashboard')

@login_required
def set_profile_role(request, role):
    """Directly set the user's profile role"""
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)
    
    profile = request.user.profile
    
    # Update profile role
    profile.role = role
    profile.save()
    
    # Update session to match profile
    request.session['selected_role'] = role
    request.session['user_role'] = role
    
    messages.success(request, f"Profile role updated to: {role}")
    return redirect('dashboard')