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

import logging
logger = logging.getLogger(__name__)

print("views.py loaded")

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

    # Calculate team and class averages for closed assessments
    if assessment.closed_date:
        team_submissions = AssessmentSubmission.objects.filter(
            assessment=assessment, student__in=request.user.teams.values_list('members__username', flat=True)
        )
        class_submissions = AssessmentSubmission.objects.filter(assessment=assessment)

        team_avg = {
            'contribution': team_submissions.aggregate(Avg('contribution'))['contribution__avg'] or "N/A",
            'teamwork': team_submissions.aggregate(Avg('teamwork'))['teamwork__avg'] or "N/A",
            'communication': team_submissions.aggregate(Avg('communication'))['communication__avg'] or "N/A",
        }

        class_avg = {
            'contribution': class_submissions.aggregate(Avg('contribution'))['contribution__avg'] or "N/A",
            'teamwork': class_submissions.aggregate(Avg('teamwork'))['teamwork__avg'] or "N/A",
            'communication': class_submissions.aggregate(Avg('communication'))['communication__avg'] or "N/A",
        }
    else:
        # Provide dummy data if the assessment is not closed
        team_avg = {
            'contribution': "N/A",
            'teamwork': "N/A",
            'communication': "N/A",
        }
        class_avg = {
            'contribution': "N/A",
            'teamwork': "N/A",
            'communication': "N/A",
        }

    context = {
        'assessment': assessment,
        'comments': comments, 
        'progress': progress,
        'team_avg': team_avg,
        'class_avg': class_avg,
    }
    
    logger.debug(f"Context: {context}")
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
        contribution = int(request.POST['contribution'])
        teamwork = int(request.POST['teamwork'])
        communication = int(request.POST['communication'])
        feedback = request.POST.get('feedback', '').strip()

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

    # Ensure the assessment is closed
    if not assessment.closed_date:
        messages.error(request, "Comments and averages are only available for closed assessments.")
        return redirect('dashboard')

    # Fetch comments for the assessment
    general_comments = AssessmentSubmission.objects.filter(assessment=assessment).values_list('student', 'feedback')
    additional_comments = AssessmentProgress.objects.filter(assessment=assessment).values_list('student__username', 'progress_notes')

    # Calculate team and class averages
    team_submissions = AssessmentSubmission.objects.filter(
        assessment=assessment, student__in=request.user.teams.values_list('members__username', flat=True)
    )
    class_submissions = AssessmentSubmission.objects.filter(assessment=assessment)

    team_avg = {
        'contribution': team_submissions.aggregate(Avg('contribution'))['contribution__avg'] or "N/A",
        'teamwork': team_submissions.aggregate(Avg('teamwork'))['teamwork__avg'] or "N/A",
        'communication': team_submissions.aggregate(Avg('communication'))['communication__avg'] or "N/A",
    }

    class_avg = {
        'contribution': class_submissions.aggregate(Avg('contribution'))['contribution__avg'] or "N/A",
        'teamwork': class_submissions.aggregate(Avg('teamwork'))['teamwork__avg'] or "N/A",
        'communication': class_submissions.aggregate(Avg('communication'))['communication__avg'] or "N/A",
    }

    context = {
        'assessment': assessment,
        'general_comments': general_comments,
        'additional_comments': additional_comments,
        'team_avg': team_avg,
        'class_avg': class_avg,
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

    current_user = UserProfile.objects.get(user=request.user)
    course = Course.objects.get(name=course_name)

    #Check if new teams have been created
    if request.method == "POST":
        print("here")
        print(request.POST)
        num_teams = request.POST['numTeams']
        for i in range(int(num_teams)):
            new_team = Team.objects.create()
            new_team.save()
            course.teams.add(new_team)
        
        messages.success(request, f"Successfully created {num_teams} new teams")
    
    user_data = {
        'preferred_name': current_user.preferred_name if current_user.preferred_name != None  else (request.user.get_full_name() or request.user.username or request.user.email.split('@')[0]),
        'real_name': request.user.get_full_name() or request.user.username or request.user.email.split('@')[0], 
        'email': request.user.email,
        'role': current_user.role,
    }

    return render(request, 'view_course.html', {
        "course": course, "teams": course.teams.all(),
        "assessments": course.assessments.all(),
        "user": user_data, "students": course.students.all()
    })

@login_required
def add_teams(request, course_name):
    
    course = Course.objects.get(name=course_name)

    return render(request, 'add_teams.html', {
        "course": course, "teams": course.teams.all()
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

from django import forms

class PeerAssessmentForm(forms.ModelForm):
    """Form for creating a single peer assessment with strict date inputs."""
    open_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    due_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Assessment
        fields = ['title', 'course', 'open_date', 'due_date', 'self_assessment_required']  # Include the new field

@login_required
def create_peer_assessments(request):
    """Allow professors to create a single peer assessment."""
    if request.user.profile.role != "professor":
        messages.error(request, "Only professors can create peer assessments.")
        return redirect('dashboard')

    if request.method == "POST":
        form = PeerAssessmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Peer assessment created successfully.")
            return redirect('dashboard')
    else:
        form = PeerAssessmentForm()

    return render(request, 'create_peer_assessments.html', {'form': form})

@login_required
def publish_assessment_results(request, assessment_id):
    """Publish assessment results to students"""
    # Check if user is a professor
    is_professor = (
        hasattr(request.user, 'profile') and request.user.profile.role == 'professor'
    ) or request.session.get('user_role') == 'professor'
    
    if not is_professor:
        messages.error(request, "Only professors can publish assessment results.")
        return redirect('dashboard')
    
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if the professor is authorized to publish this assessment
    if assessment.created_by != request.user:
        messages.error(request, "You can only publish results for assessments you created.")
        return redirect('dashboard')
    
    # Update assessment status to published
    assessment.results_published = True
    assessment.published_date = timezone.now()
    assessment.save()
    
    # Get all students who submitted this assessment
    submissions = AssessmentSubmission.objects.filter(assessment=assessment)
    students = [submission.student for submission in submissions]
    
    # Send notification emails to students
    emails_sent = 0
    for student in students:
        if not student.email:
            continue
            
        subject = f"Results Published: {assessment.title}"
        message = (
            f"Dear {student.username},\n\n"
            f"The results for '{assessment.title}' have been published. "
            f"You can now view your assessment results on the platform.\n\n"
            f"Please visit {request.build_absolute_uri('/published_results/')} to see your results.\n\n"
            "Best regards,\nPeer Assessment System"
        )
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [student.email],
                fail_silently=False
            )
            emails_sent += 1
        except Exception as e:
            messages.warning(request, f"Failed to send notification to {student.email}: {str(e)}")
    
    messages.success(request, f"Assessment results published successfully. {emails_sent} notification emails sent.")
    return redirect('view_assessment', assessment_id=assessment_id)

@login_required
def view_published_results(request, assessment_id):
    """View published assessment results for students"""
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if results are published
    if not assessment.results_published:
        messages.error(request, "Results for this assessment have not been published yet.")
        return redirect('dashboard')
    
    # Get the student's submission
    try:
        submission = AssessmentSubmission.objects.get(assessment=assessment, student=request.user)
    except AssessmentSubmission.DoesNotExist:
        messages.error(request, "You did not submit this assessment.")
        return redirect('dashboard')
    
    # Get quantitative scores
    quantitative_scores = submission.scores.filter(question__question_type='quantitative')
    average_score = quantitative_scores.aggregate(Avg('score'))['score__avg'] or 0
    
    # Get qualitative answers (anonymized and sorted)
    qualitative_answers = []
    for question in assessment.questions.filter(question_type='qualitative'):
        answers = []
        # Get all submissions for this question from all students
        all_submissions = AssessmentSubmission.objects.filter(assessment=assessment)
        for sub in all_submissions:
            answer = sub.answers.filter(question=question).first()
            if answer and answer.text_answer:
                answers.append(answer.text_answer)
        
        # Sort answers alphabetically
        answers.sort()
        
        qualitative_answers.append({
            'question': question.text,
            'answers': answers
        })
    
    context = {
        'assessment': assessment,
        'average_score': round(average_score, 2),
        'qualitative_answers': qualitative_answers,
        'submission_date': submission.submission_date
    }
    
    return render(request, 'view_published_results.html', context)