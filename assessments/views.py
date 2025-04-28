from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from authentication.models import UserProfile, AssessmentProgress
from assessments.models import Assessment, Course, Team, CourseInvitation, PeerAssessment, AssessmentSubmission, LikertQuestion, OpenEndedQuestion, LikertResponse, OpenEndedResponse, StudentScore

from django.shortcuts import HttpResponse #imports for scheduler
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.contrib.auth.models import User

#imports for averages
from django.http import JsonResponse
from django.db.models import Avg
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

from django.urls import reverse
from django.utils.safestring import mark_safe

import random
import string

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
    
    
    today = timezone.now()

    # Update assessment categorization logic
    active_assessments = Assessment.objects.filter(
        open_date__lte=today,  # Open date is in the past (already opened)
        due_date__gt=today     # Due date is in the future
    ).order_by('due_date')     # Order by due date ascending

    upcoming_assessments = Assessment.objects.filter(
        open_date__gt=today    # Open date is in the future (not yet opened)
    ).order_by('open_date')    # Order by open date ascending

    closed_assessments = Assessment.objects.filter(
        due_date__lte=today    # Due date is in the past
    ).order_by('-due_date')    # Order by due date descending (most recent first)

    # Example data for new results notification
    new_results = True  # Set this to True if there are new results to notify the student

    # Check for pending invitations
    pending_invitations_count = CourseInvitation.objects.filter(
        email=request.user.email,
        accepted=False
    ).count()
    
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
        'active_teams': request.user.teams.filter(is_active=True),
        'pending_invitations_count': pending_invitations_count
    }
    
    # Add welcome message
    messages.success(request, f"Welcome {user_data['preferred_name']} - {user_data['role']}!")
    
    return render(request, 'dashboard.html', context)

@login_required
def view_assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if assessment is active (past release date) with null check
    is_active = False
    if assessment.release_date is not None:
        is_active = timezone.now() >= assessment.release_date
    
    # Load or create draft progress
    progress, _ = AssessmentProgress.objects.get_or_create(
        student=request.user,
        assessment=assessment
    )

    # Fetch the latest submission (if it exists) by this student for this assessment
    existing_submission = AssessmentSubmission.objects.filter(
        assessment=assessment,
        student=request.user.username  # stored as CharField
    ).first()

    # Get team members (excluding self) – customize this based on your Team model
    team_members = []
    if hasattr(request.user, 'teams') and request.user.teams.exists():
        team_members = request.user.teams.first().members.exclude(username=request.user.username)

    # Get custom questions for this assessment
    likert_questions = LikertQuestion.objects.filter(assessment=assessment).order_by('order')
    open_ended_questions = OpenEndedQuestion.objects.filter(assessment=assessment).order_by('order')

    # Get team and class averages (if the assessment is closed)
    if assessment.due_date and assessment.due_date < timezone.now():
        team_usernames = team_members.values_list('username', flat=True)
        team_submissions = AssessmentSubmission.objects.filter(
            assessment=assessment, student__in=team_usernames
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
        team_avg = class_avg = {
            'contribution': "N/A",
            'teamwork': "N/A",
            'communication': "N/A",
        }

    context = {
        'assessment': assessment,
        'progress': progress,
        'submission': existing_submission,
        'team_members': team_members,
        'team_avg': team_avg,
        'class_avg': class_avg,
        'likert_questions': likert_questions,
        'open_ended_questions': open_ended_questions,
        'now': timezone.now(),
        'is_active': is_active,
    }

    return render(request, 'assessment_detail.html', context)

@login_required
def save_progress(request, assessment_id):
    """Save or overwrite in-progress data for a multi-page assessment."""
    if request.method == "POST":
        assessment = get_object_or_404(Assessment, id=assessment_id)
        progress_data = {}

        # Iterate over POST data to handle all form fields
        for key, value in request.POST.items():
            if key == 'csrfmiddlewaretoken':
                continue  # Skip CSRF token
            if isinstance(value, list) or key.endswith('[]'):  # Handle checkboxes or multiple values
                progress_data[key.rstrip('[]')] = request.POST.getlist(key)
            else:
                progress_data[key] = value

        # Retrieve or create a progress entry for the user
        progress, _ = AssessmentProgress.objects.get_or_create(
            student=request.user, assessment=assessment
        )
        progress.progress_notes = progress_data  # Save progress data as JSON
        progress.save()

        return JsonResponse({"message": "Progress saved successfully and overwritten.", "data": progress_data}, status=200)
    return JsonResponse({"error": "Invalid request method."}, status=400)

@login_required
def load_progress(request, assessment_id):
    """Load in-progress data for a multi-page assessment."""
    assessment = get_object_or_404(Assessment, id=assessment_id)
    progress = AssessmentProgress.objects.filter(student=request.user, assessment=assessment).first()

    if progress and progress.progress_notes:
        return JsonResponse(progress.progress_notes, status=200)
    return JsonResponse({}, status=200)

@login_required
def submit_assessment(request, assessment_id):
    if request.method == 'POST':
        try:
            assessment = get_object_or_404(Assessment, id=assessment_id)
            student_username = request.user.username
            assessed_username = request.POST.get('student', '').strip()
            assessed_peer = User.objects.get(username=assessed_username)

            # Get the standard fields
            contribution = int(request.POST.get('contribution', 0))
            teamwork = int(request.POST.get('teamwork', 0))
            communication = int(request.POST.get('communication', 0))
            feedback = request.POST.get('feedback', '').strip()

            # Create or update the submission
            submission, created = AssessmentSubmission.objects.update_or_create(
                assessment=assessment,
                student=student_username,
                defaults={
                    'assessed_peer': assessed_peer,
                    'contribution': contribution,
                    'teamwork': teamwork,
                    'communication': communication,
                    'feedback': feedback
                }
            )
            
            # Process Likert question responses
            likert_questions = LikertQuestion.objects.filter(assessment=assessment)
            for question in likert_questions:
                rating = request.POST.get(f'likert_{question.id}', None)
                if rating is not None:
                    LikertResponse.objects.update_or_create(
                        submission=submission,
                        question=question,
                        defaults={'rating': int(rating)}
                    )
            
            # Process open-ended question responses
            open_ended_questions = OpenEndedQuestion.objects.filter(assessment=assessment)
            for question in open_ended_questions:
                response_text = request.POST.get(f'open_ended_{question.id}', '').strip()
                if response_text:
                    OpenEndedResponse.objects.update_or_create(
                        submission=submission,
                        question=question,
                        defaults={'response_text': response_text}
                    )

            messages.success(request, "Assessment submitted successfully.")
            return redirect('dashboard')

        except User.DoesNotExist:
            messages.error(request, "Selected team member does not exist.")
        except Exception as e:
            messages.error(request, f"Error submitting assessment: {str(e)}")

    return redirect('view_assessment', assessment_id=assessment_id)

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

def generate_unique_enrollment_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not CourseInvitation.objects.filter(enrollment_code=code).exists():
            return code

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
            enrollment_code = generate_unique_enrollment_code()
        )
        num_teams = request.POST['numTeams']
        for i in range(int(num_teams)):
            Team.objects.create(course=new_course)
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
                Team.objects.create(course=course)
            
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
        "assessments": Assessment.objects.filter(course=course),
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
        course_name = request.POST.get('course_name', '').strip()
        
        # Validate course
        try:
            course = Course.objects.get(name=course_name)
            # Check if the user is the course creator
            if course.created_by != request.user:
                messages.error(request, "You can only invite students to courses you created.")
                return redirect('invite_students')
        except Course.DoesNotExist:
            messages.error(request, f"Course '{course_name}' not found.")
            return redirect('invite_students')
        
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
            emails_sent = 0
            
            for email in valid_emails:
                # Get unique enrollment code
                course = Course.objects.get(name=course_name)
                enrollment_code = course.enrollment_code

                # Create or update invitation record
                invitation, created = CourseInvitation.objects.update_or_create(
                    course=course,
                    email=email,
                    defaults={
                        'invited_by': request.user,
                        'accepted': False,
                        'enrollment_code': enrollment_code
                        }
                )
                
                subject = "Invitation to Boston College Peer Assessment System"
                message = (
                    f"Dear Student,\n\n"
                    f"You have been invited by Professor {request.user.get_full_name() or request.user.username} "
                    f"to join the Boston College Peer Assessment System for {course.name}.\n\n"
                    f"Your unique enrollment code is: {enrollment_code}\n\n"
                    f"Please visit {request.build_absolute_uri('/login/')} to log in with your BC credentials.\n\n"
                    f"After logging in, you will be prompted to enter your enrollment code to accept the invitation.\n\n"
                    "Best regards,\nPeer Assessment System"
                )

                
                try:
                    # The send_mail function will now use our custom backend
                    send_mail(
                        subject, 
                        message, 
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False
                    )
                    emails_sent += 1
                except Exception as e:
                    messages.error(request, f"Error sending to {email}: {str(e)}")
            
            if emails_sent > 0:
                messages.success(request, f"Successfully sent {emails_sent} invitation(s) for course '{course.name}'.")
            
        # Report invalid emails
        if invalid_emails:
            messages.warning(request, f"Could not send to the following emails: {', '.join(invalid_emails)}")
            
        return redirect('invite_students')
    
    # For GET requests, show the form with course selection
    courses = Course.objects.filter(created_by=request.user, is_active=True)
    return render(request, 'invite_students.html', {'courses': courses})


@login_required
def test_email(request):
    """Send a test email to verify email configuration"""
    if not request.user.is_authenticated:
        return HttpResponse("Please log in first")
    
    try:
        # Check if the user has the professor role
        is_professor = (
            hasattr(request.user, 'profile') and request.user.profile.role == 'professor'
        ) or request.session.get('user_role') == 'professor'
        
        if is_professor:
            # Import the Gmail API function
            from authentication.gmail_api import send_email_via_gmail
            
            # Try to send directly via Gmail API
            success = send_email_via_gmail(
                user=request.user,
                to=request.user.email,
                subject='Test Email from Peer Assessment System (via Gmail API)',
                body=f'This is a test email sent to {request.user.email} using the Gmail API.\n\nIf you received this, your Gmail API configuration is working!'
            )
            
            if success:
                return HttpResponse(f"Test email sent to {request.user.email} via Gmail API. Check your inbox.")
            else:
                # Fall back to regular send_mail
                send_mail(
                    'Test Email from Peer Assessment System (Fallback)',
                    f'This is a test email sent to {request.user.email} using the fallback email backend.\n\nIf you received this, your fallback email configuration is working!',
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email],
                    fail_silently=False,
                )
                return HttpResponse(f"Gmail API failed, but fallback email sent to {request.user.email}. Check your console output or email inbox.")
        else:
            # For non-professors, just use the standard email backend
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
    """Allow professors to create a single peer assessment with custom questions."""
    if request.user.profile.role != "professor":
        messages.error(request, "Only professors can create peer assessments.")
        return redirect('dashboard')

    if request.method == "POST":
        form = PeerAssessmentForm(request.POST)
        if form.is_valid():
            # Save the assessment first
            assessment = form.save()
            
            # Process Likert questions
            likert_questions = request.POST.getlist('likert_questions[]')
            for i, question_text in enumerate(likert_questions):
                if question_text.strip():  # Only save non-empty questions
                    LikertQuestion.objects.create(
                        assessment=assessment,
                        question_text=question_text,
                        order=i
                    )
            
            # Process open-ended questions
            open_ended_questions = request.POST.getlist('open_ended_questions[]')
            for i, question_text in enumerate(open_ended_questions):
                if question_text.strip():  # Only save non-empty questions
                    OpenEndedQuestion.objects.create(
                        assessment=assessment,
                        question_text=question_text,
                        order=i
                    )
            
            messages.success(request, "Peer assessment created successfully with custom questions.")
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
    
    messages.success(request, f"Test data created successfully. Assessment ID: {assessment.id}")
    # Redirect to comments view instead of assessment view
    return redirect('view_comments', assessment_id=assessment.id)

@login_required
def enroll_in_course(request):
    if request.method == "POST":
        enrollment_code = request.POST.get("enrollment_code", "").strip()
        
        if enrollment_code:
            try:
                course = Course.objects.get(enrollment_code=enrollment_code)
                course.students.add(request.user)  # Enroll the student
                messages.success(request, f"Successfully enrolled in {course.name}!")
                return redirect('view_course', course_name=course.name)
            except Course.DoesNotExist:
                return render(request, "enroll.html", {"error": "Course not found!"})
        else:
            return render(request, "enroll.html", {"error": "Please provide a course join code."})
    
    return render(request, "enroll.html")

@login_required
def debug_gmail_api(request):
    """Debug view to check Gmail API configuration"""
    from django.http import JsonResponse
    from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
    import json
    
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
    
    return JsonResponse(response_data)

@login_required
def pending_invitations(request):
    """View and accept pending course invitations."""
    # Get all invitations for the current user's email
    invitations = CourseInvitation.objects.filter(
        email=request.user.email,
        accepted=False
    ).select_related('course', 'invited_by')
    
    if request.method == 'POST':
        invitation_id = request.POST.get('invitation_id')
        action = request.POST.get('action')
        
        try:
            invitation = CourseInvitation.objects.get(id=invitation_id, email=request.user.email)
            
            if action == 'accept':
                # Add student to course
                invitation.course.students.add(request.user)
                # Mark invitation as accepted
                invitation.accepted = True
                invitation.accepted_at = timezone.now()
                invitation.save()
                
                messages.success(request, f"You have successfully enrolled in {invitation.course.name}.")
            elif action == 'decline':
                # Delete the invitation
                invitation.delete()
                messages.info(request, f"You have declined the invitation to {invitation.course.name}.")
                
        except CourseInvitation.DoesNotExist:
            messages.error(request, "Invalid invitation.")
        
        return redirect('pending_invitations')
    
    return render(request, 'pending_invitations.html', {'invitations': invitations})

@login_required
def get_pending_invitations_json(request):
    """Return pending invitations as JSON for AJAX requests."""
    invitations = CourseInvitation.objects.filter(
        email=request.user.email,
        accepted=False
    ).select_related('course', 'invited_by')
    
    invitations_data = []
    for invitation in invitations:
        invitations_data.append({
            'id': invitation.id,
            'course_name': invitation.course.name,
            'course_code': invitation.course.course_code,
            'invited_by': invitation.invited_by.get_full_name() or invitation.invited_by.username,
            'created_at': invitation.created_at.strftime('%b %d, %Y')
        })
    
    return JsonResponse({'invitations': invitations_data})

@login_required
def accept_invitation(request):
    """Accept or decline an invitation via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
    
    invitation_id = request.POST.get('invitation_id')
    action = request.POST.get('action')
    entered_code = request.POST.get('enrollment_code', '').strip()  # <- get the entered code
    
    try:
        invitation = CourseInvitation.objects.get(id=invitation_id, email=request.user.email)
        
        if action == 'accept':
            # Check if the entered code matches
            if invitation.enrollment_code != entered_code:
                messages.error(request, "Incorrect enrollment code. Please try again.")
                return redirect('pending_invitations')
            
            # Code matches, accept the invitation
            invitation.course.students.add(request.user)
            invitation.accepted = True
            invitation.accepted_at = timezone.now()
            invitation.save()
            
            messages.success(request, f"You have successfully enrolled in {invitation.course.name}.")
        elif action == 'decline':
            # Delete the invitation
            invitation.delete()
            messages.info(request, f"You have declined the invitation to {invitation.course.name}.")
            
    except CourseInvitation.DoesNotExist:
        messages.error(request, "Invalid invitation.")
    
    return redirect('dashboard')


@login_required
def edit_assessment_questions(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if user is a professor
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'professor':
        messages.error(request, "You don't have permission to edit assessment questions.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    # Check if assessment is already published
    if assessment.is_published:
        messages.error(request, "This assessment has already been published and cannot be modified.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    # Check if assessment is active (past release date) with null check
    if assessment.release_date is not None and timezone.now() >= assessment.release_date:
        messages.error(request, "This assessment is currently active and cannot be modified.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        
        # Process Likert questions
        likert_count = int(request.POST.get('likert_count', 0))
        for i in range(1, likert_count + 1):
            question_id = request.POST.get(f'likert_id_{i}')
            question_text = request.POST.get(f'likert_text_{i}')
            question_order = int(request.POST.get(f'likert_order_{i}', i))
            
            if question_id == 'new':
                # Create new question
                LikertQuestion.objects.create(
                    assessment=assessment,
                    question_text=question_text,
                    order=question_order
                )
            else:
                # Update existing question
                try:
                    question = LikertQuestion.objects.get(id=question_id, assessment=assessment)
                    question.question_text = question_text
                    question.order = question_order
                    question.save()
                except LikertQuestion.DoesNotExist:
                    # Question was deleted or doesn't belong to this assessment
                    pass
        
        # Process Open-ended questions
        open_ended_count = int(request.POST.get('open_ended_count', 0))
        for i in range(1, open_ended_count + 1):
            question_id = request.POST.get(f'open_ended_id_{i}')
            question_text = request.POST.get(f'open_ended_text_{i}')
            question_order = int(request.POST.get(f'open_ended_order_{i}', i))
            
            if question_id == 'new':
                # Create new question
                OpenEndedQuestion.objects.create(
                    assessment=assessment,
                    question_text=question_text,
                    order=question_order
                )
            else:
                # Update existing question
                try:
                    question = OpenEndedQuestion.objects.get(id=question_id, assessment=assessment)
                    question.question_text = question_text
                    question.order = question_order
                    question.save()
                except OpenEndedQuestion.DoesNotExist:
                    # Question was deleted or doesn't belong to this assessment
                    pass
        
        # Delete questions that weren't included in the form
        existing_likert_ids = [request.POST.get(f'likert_id_{i}') for i in range(1, likert_count + 1) 
                              if request.POST.get(f'likert_id_{i}') != 'new']
        LikertQuestion.objects.filter(assessment=assessment).exclude(id__in=existing_likert_ids).delete()
        
        existing_open_ended_ids = [request.POST.get(f'open_ended_id_{i}') for i in range(1, open_ended_count + 1)
                                  if request.POST.get(f'open_ended_id_{i}') != 'new']
        OpenEndedQuestion.objects.filter(assessment=assessment).exclude(id__in=existing_open_ended_ids).delete()
        
        # Handle publishing if requested
        if action == 'publish':
            assessment.is_published = True
            assessment.save()
            
            # Send confirmation email about publishing
            send_mail(
                f'Assessment Published: {assessment.title}',
                f'''You have successfully published the assessment "{assessment.title}" in course "{assessment.course.name}".
                
The assessment will be released to students on {assessment.release_date}.

This is an automated message from the Peer Assessment System.''',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
            )
            
            messages.success(request, "Assessment has been published successfully. A confirmation email has been sent.")
        else:
            # Send confirmation email about saving draft
            send_mail(
                f'Assessment Draft Updated: {assessment.title}',
                f'''You have successfully updated the draft for assessment "{assessment.title}" in course "{assessment.course.name}".
                
The assessment is saved as a draft and can still be edited. It will be released to students on {assessment.release_date} if published.
                
This is an automated message from the Peer Assessment System.''',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
            )
            
            messages.success(request, "Assessment draft has been saved successfully. A confirmation email has been sent.")
            
        return redirect('view_assessment', assessment_id=assessment_id)
    
    # If not POST, redirect back to the assessment view
    return redirect('view_assessment', assessment_id=assessment_id)

@login_required
def view_team_comments(request, assessment_id, team_id=None):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if user is a professor or a student in the team
    is_professor = hasattr(request.user, 'profile') and request.user.profile.role == 'professor'
    
    if not is_professor:
        # For students, only allow viewing their own team's comments
        user_team = Team.objects.filter(course=assessment.course, members=request.user).first()
        if not user_team:
            messages.error(request, "You are not part of any team in this course.")
            return redirect('view_assessment', assessment_id=assessment_id)
        
        if team_id and int(team_id) != user_team.id:
            messages.error(request, "You can only view comments for your own team.")
            return redirect('view_assessment', assessment_id=assessment_id)
        
        team = user_team
    else:
        # For professors, allow viewing any team's comments
        if team_id:
            team = get_object_or_404(Team, id=team_id, course=assessment.course)
        else:
            # If no team specified, show the first team
            team = Team.objects.filter(course=assessment.course).first()
            if not team:
                messages.error(request, "No teams found for this course.")
                return redirect('view_assessment', assessment_id=assessment_id)
    
    # Get all teams for the dropdown (for professors)
    teams = Team.objects.filter(course=assessment.course) if is_professor else None
    
    # Get team members
    team_members = team.members.all()
    
    # Get all submissions for this assessment and team
    submissions = AssessmentSubmission.objects.filter(
        assessment=assessment,
        student__in=team_members,
        peer__in=team_members
    )
    
    # Organize comments by recipient
    comments_by_recipient = {}
    for member in team_members:
        member_submissions = submissions.filter(peer=member)
        
        # Get open-ended responses
        open_ended_responses = []
        for submission in member_submissions:
            responses = OpenEndedResponse.objects.filter(submission=submission)
            for response in responses:
                # Anonymize the reviewer for students
                reviewer = submission.student.get_full_name() or submission.student.username
                if not is_professor and submission.student != request.user:
                    reviewer = "Anonymous Team Member"
                
                open_ended_responses.append({
                    'question': response.question.question_text,
                    'response': response.response_text,
                    'reviewer': reviewer
                })
        
        comments_by_recipient[member] = open_ended_responses
    
    # Get or create scores for each team member
    member_scores = {}
    for member in team_members:
        score = StudentScore.objects.filter(
            student=member,
            assessment=assessment
        ).first()
        member_scores[member.id] = score.score if score else None

    context = {
        'assessment': assessment,
        'team': team,
        'teams': teams,
        'is_professor': is_professor,
        'comments_by_recipient': comments_by_recipient,
        'member_scores': member_scores,  # Add scores to context
    }
    
    return render(request, 'team_comments.html', context)

@login_required
def get_team_members(request, team_id):
    """AJAX endpoint to get team members"""
    team = get_object_or_404(Team, id=team_id)
    members = [{
        'id': member.id,
        'name': member.get_full_name() or member.username
    } for member in team.members.all()]
    return JsonResponse({'members': members})

@login_required
def submit_student_score(request):
    """AJAX endpoint to submit a student's score"""
    if request.method != 'POST' or not request.user.profile.role == 'professor':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        assessment_id = request.POST.get('assessment_id')
        student_id = request.POST.get('student_id')
        score = float(request.POST.get('score'))
        
        if score < 0 or score > 10:
            return JsonResponse({'error': 'Score must be between 0 and 10'}, status=400)
            
        assessment = get_object_or_404(Assessment, id=assessment_id)
        student = get_object_or_404(User, id=student_id)
        
        # Save or update the student's score
        student_score, created = StudentScore.objects.update_or_create(
            student=student,
            assessment=assessment,
            defaults={'score': score}
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Score of {score} saved for {student.get_full_name() or student.username}'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
