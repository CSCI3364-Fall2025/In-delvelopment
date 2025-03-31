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

from django.urls import reverse
from django.utils.safestring import mark_safe

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
    
    # Replace the hardcoded lists with database queries
    active_assessments = Assessment.objects.filter(
        closed_date__isnull=True,
        open_date__isnull=True
    ).order_by('due_date')
    
    closed_assessments = Assessment.objects.filter(
        closed_date__isnull=False
    ).order_by('-closed_date')
    
    upcoming_assessments = Assessment.objects.filter(
        open_date__isnull=False
    ).order_by('open_date')
    
    # Example data for new results notification
    new_results = True  # Set this to True if there are new results to notify the student

    context = {
        'user': user_data,
        'active_assessments': active_assessments,
        'closed_assessments': closed_assessments,
        'upcoming_assessments': upcoming_assessments,
        'num_uncompleted_assessments': active_assessments.count(),
        'num_assessment_results': closed_assessments.count(),
        'new_results': new_results,
        'request': request,
        'active_courses': request.user.courses.filter(is_active=True) | request.user.created_courses.filter(is_active=True),
        'active_teams': request.user.teams.filter(is_active=True)
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

    # If no progress exists, create an empty one (but don't save it)
    if not progress:
        progress = AssessmentProgress(student=request.user, assessment=assessment, progress_notes="")

    # Pass the progress object to the context and render the assessment detail page
    context = {
        'assessment': assessment,
        'progress': progress,
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
    """View all published assessment results for a student"""
    # Get all assessments with published results
    published_assessments = Assessment.objects.filter(results_published=True)
    
    # Filter to only include assessments the student has submitted
    student_assessments = []
    for assessment in published_assessments:
        try:
            submission = AssessmentSubmission.objects.get(assessment=assessment, student=request.user.username)
            student_assessments.append({
                'assessment': assessment,
                'submission': submission
            })
        except AssessmentSubmission.DoesNotExist:
            continue
    
    context = {
        'student_assessments': student_assessments
    }
    
    return render(request, 'all_published_results.html', context)

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

    #Check if teams have been created / updated
    if request.method == "POST":
        # Check if teams are getting added
        if request.POST.get('numTeams') != None:
            num_teams = request.POST['numTeams']
            for i in range(int(num_teams)):
                new_team = Team.objects.create()
                new_team.save()
                course.teams.add(new_team)
            
            messages.success(request, f"Successfully created {num_teams} new teams.")
        else: 
            # teams are being updated
            team = Team.objects.get(pk=request.POST['team_pk'])
            team_name = request.POST['teamName']
            new_members = request.POST['addMembers']
            remove_members = request.POST['removeMembers']
            print(new_members)
            print(remove_members)

            team.name = team_name
            if new_members != "None":
                for member_pk in new_members:
                    if member_pk != "Choose students to add to team.":
                        student = User.objects.get(pk=member_pk)
                        team.members.add(student)
            
            if remove_members != "None":
                for member_pk in remove_members:
                    if member_pk != "Choose students to remove from team.":
                        student = User.objects.get(pk=member_pk)
                        team.members.remove(student)

            team.save()
            messages.success(request, f"Team updated successfully.")
    
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
def edit_team(request, course_name, team_pk):
    
    team = Team.objects.get(pk=team_pk)
    course = Course.objects.get(name=course_name)

    return render(request, 'edit_team.html', {
        "team": team, "course": course,
        "students": course.students.all(),
        "team_members": team.members.all()
    })

@login_required
def delete_team(request, course_name, team_pk):

    team = Team.objects.get(pk=team_pk)
    team.delete()

    messages.success(request, f"Team deleted successfully.")
    return redirect('view_course', course_name=course_name)

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
    
    # Update assessment status to published
    assessment.results_published = True
    assessment.published_date = timezone.now()
    assessment.save()
    
    # Get all students who submitted this assessment
    submissions = AssessmentSubmission.objects.filter(assessment=assessment)
    
    # Send notification emails to students
    emails_sent = 0
    for submission in submissions:
        # Try to get the User object for the student
        try:
            student_user = User.objects.get(username=submission.student)
        except User.DoesNotExist:
            # If no user exists with this username, try to find by email
            try:
                student_user = User.objects.get(email=submission.student)
            except User.DoesNotExist:
                # Skip if we can't find the user
                continue
        
        # Skip if no email is available
        if not hasattr(student_user, 'email') or not student_user.email:
            continue
            
        subject = f"Results Published: {assessment.title}"
        message = (
            f"Dear {student_user.username},\n\n"
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
                [student_user.email],
                fail_silently=False
            )
            emails_sent += 1
        except Exception as e:
            messages.warning(request, f"Failed to send notification to {student_user.email}: {str(e)}")
    
    messages.success(request, f"Assessment results published successfully. {emails_sent} notification emails sent.")
    return redirect('view_comments', assessment_id=assessment_id)

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
        submission = AssessmentSubmission.objects.get(assessment=assessment, student=request.user.username)
    except AssessmentSubmission.DoesNotExist:
        messages.error(request, "You did not submit this assessment.")
        return redirect('dashboard')
    
    # Calculate average score for quantitative questions
    avg_score = (submission.contribution + submission.teamwork + submission.communication) / 3.0
    
    # Get qualitative answers (feedback) from all submissions for this assessment
    all_feedback = []
    submissions = AssessmentSubmission.objects.filter(assessment=assessment)
    for sub in submissions:
        if sub.feedback:
            all_feedback.append(sub.feedback)
    
    # Sort feedback alphabetically
    all_feedback.sort()
    
    context = {
        'assessment': assessment,
        'average_score': round(avg_score, 2),
        'qualitative_answers': all_feedback,
        'submission_date': submission.submitted_at if hasattr(submission, 'submitted_at') else None
    }
    
    return render(request, 'view_published_results.html', context)

@login_required
def create_test_data(request):
    """Create test data for assessment publishing functionality"""
    if not request.user.is_superuser:
        messages.error(request, "Only superusers can create test data.")
        return redirect('dashboard')
    
    # Create a test assessment that's already closed
    assessment = Assessment.objects.create(
        title="Test Assessment",
        course="Test Course",
        due_date=timezone.now() - timedelta(days=1),  # Due date in the past
        closed_date=timezone.now() - timedelta(hours=12),  # Already closed
        results_published=False  # Not yet published
    )
    
    # Create test students if needed
    test_students = []
    for i in range(3):
        username = f"teststudent{i+1}"
        email = f"{username}@bc.edu"
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email}
        )
        if created:
            user.set_password("testpassword")
            user.save()
            # Only create profile if it doesn't exist
            UserProfile.objects.get_or_create(user=user, defaults={'role': "student"})
        test_students.append(user)
    
    # Create a test professor if needed
    prof_username = "testprofessor"
    prof_email = f"{prof_username}@bc.edu"
    prof_user, prof_created = User.objects.get_or_create(
        username=prof_username,
        defaults={'email': prof_email}
    )
    if prof_created:
        prof_user.set_password("testpassword")
        prof_user.save()
        UserProfile.objects.get_or_create(user=prof_user, defaults={'role': "professor"})
    
    # Create test submissions with varied feedback to test alphabetical sorting
    feedback_comments = [
        "Excellent presentation with clear explanations.",
        "Appreciated the detailed examples provided.",
        "Visuals were helpful but could be improved.",
        "Collaboration was effective throughout the project.",
        "Better communication would have improved outcomes.",
        "Deadlines were consistently met by the team."
    ]
    
    # Ensure we have enough feedback options
    while len(feedback_comments) < len(test_students):
        feedback_comments.append(f"Additional feedback item {len(feedback_comments) + 1}.")
    
    # Create submissions for each student
    for i, student in enumerate(test_students):
        # Check if a submission already exists
        if not AssessmentSubmission.objects.filter(assessment=assessment, student=student.username).exists():
            # Create submission with randomized scores and feedback
            contribution = 3 + (i % 3)  # Scores between 3-5
            teamwork = 2 + (i % 4)      # Scores between 2-5
            communication = 3 + ((i+1) % 3)  # Scores between 3-5
            
            # Select two different feedback items for each student
            primary_feedback_idx = i % len(feedback_comments)
            secondary_feedback_idx = (i + 3) % len(feedback_comments)
            
            feedback = feedback_comments[primary_feedback_idx]
            
            # Create the submission
            AssessmentSubmission.objects.create(
                assessment=assessment,
                student=student.username,
                contribution=contribution,
                teamwork=teamwork,
                communication=communication,
                feedback=feedback
            )
            
            # Create a second submission with different feedback for variety
            AssessmentSubmission.objects.create(
                assessment=assessment,
                student=f"peer{i+1}",  # Fictional peer
                contribution=4,
                teamwork=4,
                communication=4,
                feedback=feedback_comments[secondary_feedback_idx]
            )
    
<<<<<<< HEAD
    # Create progress notes for some students
    for i, student in enumerate(test_students):
        if i % 2 == 0:  # Only for some students
            progress, _ = AssessmentProgress.objects.get_or_create(
                student=student,
                assessment=assessment,
                defaults={
                    'progress_notes': f"Additional notes from {student.username}: This assessment helped me understand the material better."
                }
            )
    
    messages.success(request, mark_safe(f"""
        <strong>Test data created successfully. Assessment ID: {assessment.id}</strong><br>
        <div class="mt-3">
            <h5>Quick Actions:</h5>
            <a href="{reverse('view_comments', kwargs={'assessment_id': assessment.id})}" class="btn btn-primary">View & Publish Results</a>
            {student_links_html}
            <button onclick="openStudentViews()" class="btn btn-success">Open All Student Views</button>
        </div>
    """))
    
    # Redirect to comments view for the professor to publish
    return redirect('view_comments', assessment_id=assessment.id)

@login_required
def view_as_student(request, username, assessment_id):
    """View assessment results as if you were a specific student (admin only)"""
    if not request.user.is_superuser:
        messages.error(request, "Only superusers can use this feature.")
        return redirect('dashboard')
    
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if results are published
    if not assessment.results_published:
        messages.error(request, "Results for this assessment have not been published yet.")
        return redirect('dashboard')
    
    # Get the student's submission
    try:
        submission = AssessmentSubmission.objects.get(assessment=assessment, student=username)
    except AssessmentSubmission.DoesNotExist:
        messages.error(request, f"User {username} did not submit this assessment.")
        return redirect('dashboard')
    
    # Calculate average score for quantitative questions
    avg_score = (submission.contribution + submission.teamwork + submission.communication) / 3.0
    
    # Get qualitative answers (feedback) from all submissions for this assessment
    all_feedback = []
    submissions = AssessmentSubmission.objects.filter(assessment=assessment)
    for sub in submissions:
        if sub.feedback:
            all_feedback.append(sub.feedback)
    
    # Sort feedback alphabetically
    all_feedback.sort()
    
    context = {
        'assessment': assessment,
        'average_score': round(avg_score, 2),
        'qualitative_answers': all_feedback,
        'submission_date': submission.submitted_at if hasattr(submission, 'submitted_at') else None,
        'viewing_as': username,
        'is_preview': True
    }
    
    return render(request, 'view_published_results.html', context)
=======
    messages.success(request, f"Test data created successfully. Assessment ID: {assessment.id}")
    # Redirect to comments view instead of assessment view
    return redirect('view_comments', assessment_id=assessment.id)



@login_required
def enroll_in_course(request):
    if request.method == "POST":
        course_name = request.POST.get("course_name", "").strip()
        
        if course_name:
            try:
                course = Course.objects.get(name=course_name)
                course.students.add(request.user)  # Enroll the student
                return render(request, "course_details.html", {"message": "Course details coming soon"})
            except Course.DoesNotExist:
                return render(request, "enroll.html", {"error": "Course not found!"})
        else:
            return render(request, "enroll.html", {"error": "Please provide a course name."})
    
    return render(request, "enroll.html")
>>>>>>> 2831bb3 (made it so students can enroll to classes and edited the saving functionality)
