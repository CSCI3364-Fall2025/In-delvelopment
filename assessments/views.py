from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from authentication.models import UserProfile, AssessmentProgress
from assessments.models import Assessment, Course, Team, CourseInvitation, PeerAssessment, AssessmentSubmission, LikertQuestion, OpenEndedQuestion, LikertResponse, OpenEndedResponse, StudentScore, Enrollment

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
from .forms import PeerAssessmentForm

import logging
logger = logging.getLogger(__name__)

from django.urls import reverse
from django.utils.safestring import mark_safe

import random
import string
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError

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
    
    # Get all courses from the database
    from assessments.models import Course, Assessment
    from django.utils import timezone
    from django.db.models import Q  # Add this import for Q objects
    
    # Get courses based on role
    if current_user.role == 'professor':
        # Professors see courses they created
        courses = Course.objects.filter(created_by=request.user)
    else:
        # Students see courses they're enrolled in
        courses = Course.objects.filter(students=request.user)
    
    # For testing: if no courses are found, show all courses
    if not courses.exists():
        courses = Course.objects.all()
    
    # Get assessments and categorize them
    now = timezone.now()
    
    # Active assessments: due date is in the future or no due date
    active_assessments = Assessment.objects.filter(
        Q(due_date__gt=now) | Q(due_date__isnull=True),  # Use Q directly, not models.Q
        course__in=courses
    ).order_by('due_date')
    
    # Past assessments: due date is in the past
    past_assessments = Assessment.objects.filter(
        due_date__lt=now,
        course__in=courses
    ).order_by('-due_date')
    
    # Prepare context with all data
    context = {
        'user_data': user_data,
        'courses': courses,
        'active_assessments': active_assessments,
        'past_assessments': past_assessments,
        'is_professor': current_user.role == 'professor',
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def view_assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    now = timezone.now()
    
    # Check if assessment is active or published
    is_active = assessment.open_date <= now and assessment.due_date > now
    
    # Get the user's team for this assessment's course
    team = None
    teams = []
    
    if hasattr(request.user, 'teams'):
        for user_team in request.user.teams.all():
            if user_team.course == assessment.course:
                team = user_team
                break
    
    # For professors, get all teams in the course
    if hasattr(request.user, 'profile') and request.user.profile.role == 'professor':
        teams = Team.objects.filter(course=assessment.course)
    
    # Get team members if user is in a team
    team_members = []
    teammates = []
    if team:
        team_members = team.members.all()
        teammates = [member for member in team_members if member != request.user]
    
    # Get all submissions by this user for this assessment
    user_submissions = {}
    if request.user.is_authenticated:
        submissions = AssessmentSubmission.objects.filter(
            assessment=assessment,
            student=request.user
        )
        
        # Organize submissions by assessed peer
        for submission in submissions:
            if submission.assessed_peer:
                user_submissions[submission.assessed_peer.username] = submission
    
    # Get likert and open-ended questions
    likert_questions = LikertQuestion.objects.filter(assessment=assessment).order_by('order')
    open_ended_questions = OpenEndedQuestion.objects.filter(assessment=assessment).order_by('order')
    
    # Get selected team for averages (default to user's team)
    selected_team_id = request.GET.get('team_id')
    selected_team = None
    
    if selected_team_id:
        try:
            selected_team = Team.objects.get(id=selected_team_id, course=assessment.course)
        except Team.DoesNotExist:
            selected_team = team
    else:
        selected_team = team
    
    # Calculate team and class averages
    team_avg = {
        'contribution': 0,
        'teamwork': 0,
        'communication': 0
    }
    
    class_avg = {
        'contribution': 0,
        'teamwork': 0,
        'communication': 0
    }
    
    # Calculate team averages if a team is selected
    if selected_team:
        team_submissions = AssessmentSubmission.objects.filter(
            assessment=assessment,
            student__in=selected_team.members.all()
        )
        
        if team_submissions.exists():
            team_avg['contribution'] = team_submissions.aggregate(Avg('contribution'))['contribution__avg'] or 0
            team_avg['teamwork'] = team_submissions.aggregate(Avg('teamwork'))['teamwork__avg'] or 0
            team_avg['communication'] = team_submissions.aggregate(Avg('communication'))['communication__avg'] or 0
    
    # Calculate class averages
    all_submissions = AssessmentSubmission.objects.filter(assessment=assessment)
    if all_submissions.exists():
        class_avg['contribution'] = all_submissions.aggregate(Avg('contribution'))['contribution__avg'] or 0
        class_avg['teamwork'] = all_submissions.aggregate(Avg('teamwork'))['teamwork__avg'] or 0
        class_avg['communication'] = all_submissions.aggregate(Avg('communication'))['communication__avg'] or 0
    
    # Variables for team submissions section
    team_submission_members = []
    team_submission_data = []
    submission_matrix = {}
    completed_members = set()
    completion_percentage = 0
    
    # Handle team submissions section (for professors)
    if hasattr(request.user, 'profile') and request.user.profile.role == 'professor':
        # Get selected team for submissions view
        team_id = request.GET.get('team_id')  # Use the same parameter as the form
        selected_team = None
        
        if team_id:
            try:
                selected_team = Team.objects.get(id=team_id, course=assessment.course)
                
                # Get team members
                team_members = list(selected_team.members.all())
                
                # Initialize submission matrix
                for evaluator in team_members:
                    submission_matrix[evaluator.id] = {}
                    for evaluated in team_members:
                        submission_matrix[evaluator.id][evaluated.id] = None
                
                # Track which members have completed all their assessments
                member_completion = {member.id: 0 for member in team_members}
                required_submissions = len(team_members) - 1  # Excluding self-assessment
                
                # Get all submissions for this team and assessment
                team_submissions_data = []
                all_team_submissions = AssessmentSubmission.objects.filter(
                    assessment=assessment,
                    student__in=team_members
                ).select_related('student', 'assessed_peer')
                
                # Process each submission
                for submission in all_team_submissions:
                    if submission.assessed_peer and submission.assessed_peer in team_members:
                        # Add to the matrix
                        submission_matrix[submission.student.id][submission.assessed_peer.id] = submission
                        
                        # Count this submission for completion tracking
                        member_completion[submission.student.id] += 1
                        
                        # Add to the list for display
                        team_submission_data.append({
                            'student': submission.student,
                            'submission': submission,
                            'assessed_peer': submission.assessed_peer,
                            'submission_date': submission.submitted_at
                        })
                
                # Determine which members have completed all their assessments
                for member_id, count in member_completion.items():
                    if count >= required_submissions:
                        completed_members.add(member_id)
                
                # Calculate completion percentage
                completion_percentage = int(len(completed_members) / len(team_members) * 100) if team_members else 0
                
            except Team.DoesNotExist:
                pass
    
    # Initialize context dictionary
    context = {
        'assessment': assessment,
        'is_active': is_active,
        'team': team,
        'teams': teams,
        'selected_team': selected_team,
        'team_members': team_members,
        'teammates': teammates,
        'user_submissions': user_submissions,
        'likert_questions': likert_questions,
        'open_ended_questions': open_ended_questions,
        'team_avg': team_avg,
        'class_avg': class_avg,
        # Team submissions section variables
        'team_submission': selected_team if 'selected_team' in locals() else None,
        'team_submission_members': team_submission_members,
        'team_submission_data': team_submission_data,
        'submission_matrix': submission_matrix,
        'completed_members': completed_members,
        'completion_percentage': completion_percentage
    }
    
    # For professors, collect all submissions by team
    all_submissions = {}
    if hasattr(request.user, 'profile') and request.user.profile.role == 'professor':
        # Get all teams in this course
        teams = Team.objects.filter(course=assessment.course)
        
        # Initialize the all_submissions dictionary with team IDs as keys
        for team in teams:
            all_submissions[team.id] = []
        
        # Add a key for students not in teams
        all_submissions['no_team'] = []
        
        # Get all submissions for this assessment
        all_assessment_submissions = AssessmentSubmission.objects.filter(assessment=assessment)
        
        # Group submissions by team
        for submission in all_assessment_submissions:
            # Find which team the student belongs to
            student_teams = Team.objects.filter(course=assessment.course, members=submission.student)
            
            if student_teams.exists():
                team = student_teams.first()
                # Add submission to the team's list
                all_submissions[team.id].append({
                    'student': submission.student,
                    'submission': submission
                })
            else:
                # Student is not in a team
                all_submissions['no_team'].append({
                    'student': submission.student,
                    'submission': submission
                })
    
    context['all_submissions'] = all_submissions
    
    # Add a custom template filter for accessing dictionary items by key
    from django.template.defaulttags import register
    
    @register.filter
    def get_item(dictionary, key):
        return dictionary.get(key)
    
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
    if request.method != 'POST':
        return redirect('view_assessment', assessment_id=assessment_id)
    
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if assessment is still open
    now = timezone.now()
    if now > assessment.due_date and not request.user.is_staff:
        messages.error(request, "This assessment is closed.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    # Get form data
    peer_id = request.POST.get('peer_id')
    contribution = request.POST.get('contribution')
    teamwork = request.POST.get('teamwork')
    communication = request.POST.get('communication')
    feedback = request.POST.get('feedback', '')
    
    # Validate data with specific error messages
    missing_fields = []
    if not peer_id:
        missing_fields.append("Peer")
    if not contribution:
        missing_fields.append("Contribution")
    if not teamwork:
        missing_fields.append("Teamwork")
    if not communication:
        missing_fields.append("Communication")
    
    if missing_fields:
        error_message = f"Missing required fields: {', '.join(missing_fields)}"
        messages.error(request, error_message)
        return redirect('view_assessment', assessment_id=assessment_id)
    
    try:
        peer = User.objects.get(id=peer_id)
        
        # Check if a submission already exists for this peer
        existing_submission = AssessmentSubmission.objects.filter(
            assessment=assessment,
            student=request.user,
            assessed_peer=peer
        ).first()
        
        if existing_submission:
            # Update existing submission
            existing_submission.contribution = contribution
            existing_submission.teamwork = teamwork
            existing_submission.communication = communication
            existing_submission.feedback = feedback
            existing_submission.submitted_at = timezone.now()
            existing_submission.save()
            
            # Delete existing responses to avoid duplicates
            if hasattr(existing_submission, 'likert_responses'):
                LikertResponse.objects.filter(submission=existing_submission).delete()
            if hasattr(existing_submission, 'open_ended_responses'):
                OpenEndedResponse.objects.filter(submission=existing_submission).delete()
            
            submission = existing_submission
            messages.success(request, f"Your assessment of {peer.get_full_name() or peer.username} has been updated.")
        else:
            # Create new submission
            try:
                submission = AssessmentSubmission.objects.create(
                    assessment=assessment,
                    student=request.user,
                    assessed_peer=peer,
                    contribution=contribution,
                    teamwork=teamwork,
                    communication=communication,
                    feedback=feedback
                )
                messages.success(request, f"Your assessment of {peer.get_full_name() or peer.username} has been submitted.")
            except IntegrityError:
                # This happens when there's a unique constraint violation
                messages.error(request, f"You've already submitted an assessment for {peer.get_full_name() or peer.username}. Please refresh the page to see your existing submission.")
                return redirect('view_assessment', assessment_id=assessment_id)
        
        # Process likert questions
        for key, value in request.POST.items():
            if key.startswith('likert_'):
                question_id = key.split('_')[1]
                try:
                    question = LikertQuestion.objects.get(id=question_id)
                    LikertResponse.objects.create(
                        submission=submission,
                        question=question,
                        rating=value
                    )
                except LikertQuestion.DoesNotExist:
                    continue
                except Exception as e:
                    print(f"Error creating likert response: {str(e)}")
        
        # Process open-ended questions
        for key, value in request.POST.items():
            if key.startswith('openended_') and value.strip():
                question_id = key.split('_')[1]
                try:
                    question = OpenEndedQuestion.objects.get(id=question_id)
                    OpenEndedResponse.objects.create(
                        submission=submission,
                        question=question,
                        response_text=value
                    )
                except OpenEndedQuestion.DoesNotExist:
                    continue
                except Exception as e:
                    print(f"Error creating open-ended response: {str(e)}")
        
        return redirect('view_assessment', assessment_id=assessment_id)
    
    except IntegrityError:
        # This is a more general catch for any IntegrityError
        peer_name = peer.get_full_name() or peer.username if 'peer' in locals() else "this peer"
        messages.error(request, f"You've already submitted an assessment for {peer_name}. Please refresh the page to see your existing submission.")
        return redirect('view_assessment', assessment_id=assessment_id)
    except Exception as e:
        # Make the error message more user-friendly
        if "UNIQUE constraint failed" in str(e):
            peer_name = peer.get_full_name() or peer.username if 'peer' in locals() else "this peer"
            messages.error(request, f"You've already submitted an assessment for {peer_name}. Please refresh the page to see your existing submission.")
        else:
            messages.error(request, f"Error submitting assessment: {str(e)}")
        
        # Log the detailed error for debugging
        import traceback
        print(traceback.format_exc())
        
        return redirect('view_assessment', assessment_id=assessment_id)


def get_teammates(user, course):
    """Helper function to get all teammates for a user in a course"""
    teams = Team.objects.filter(course=course, members=user)
    if teams.exists():
        team = teams.first()
        return team.members.all()
    return User.objects.none()

@login_required
def view_all_published_results(request):
    """View all published assessment results for a student"""
    # Get all assessments with published results
    published_assessments = Assessment.objects.filter(results_published=True)
    
    # Filter to only include assessments the student has submitted
    student_assessments = []
    for assessment in published_assessments:
        try:
            submission = AssessmentSubmission.objects.get(assessment=assessment, student=request.user)
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
        send_course_creation_email(request.user, new_course)
        messages.success(request, f"Successfully created course '{new_course.name}'")   

    if request.user.profile.role == "professor":
        courses = request.user.created_courses.filter(is_active=True)
    else:
        courses = request.user.courses.filter(is_active=True)

    return render(request, 'course_dashboard.html', {
        "user": user_data, "courses": courses,
        "closed_courses": request.user.courses.filter(is_active=False)
    })

def send_course_creation_email(professor, course):
    subject = f"Course Created: {course.name}"
    message = (
        f"Dear {professor.get_full_name() or professor.username},\n\n"
        f"You have successfully created the course \"{course.name}\" for {course.semester} {course.year}.\n\n"
        f"Students can join this course using the enrollment code: {course.enrollment_code}\n\n"
        "Please share this code with your students so they can enroll.\n\n"
        "Best regards,\nYour Peer Assessment System Team"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [professor.email],
        fail_silently=False,
    )


@login_required
def create_course(request):
    return render(request, 'create_course.html')

@login_required
def view_course(request, course_id, course_name=None):
    """View a specific course."""
    try:
        course = Course.objects.get(pk=course_id)
        
        # Check if the course name in the URL matches the actual course name
        if course_name and course_name != course.name:
            # Redirect to the correct URL if the name doesn't match
            return redirect('view_course', course_name=course.name, course_id=course_id)
        
        # Check if user is enrolled or is the creator
        is_enrolled = request.user in course.students.all()
        is_creator = request.user == course.created_by
        
        if not (is_enrolled or is_creator):
            messages.error(request, "You are not enrolled in this course.")
            return redirect('dashboard')
        
        # Get assessments for this course - use the correct related name or query
        # If there's a related name defined in your model, use that instead
        try:
            # Try to get assessments using the related name if it exists
            assessments = course.assessments.all()
        except AttributeError:
            # If the related name doesn't exist, try to query directly
            from assessments.models import Assessment  # Import the Assessment model
            assessments = Assessment.objects.filter(course=course)
        
        # Get teams for this course
        teams = Team.objects.filter(course=course)
        
        # Check if the user is on a team
        user_team = None
        for team in teams:
            if request.user in team.members.all():
                user_team = team
                break
        
        context = {
            'course': course,
            'assessments': assessments,
            'is_enrolled': is_enrolled,
            'is_creator': is_creator,
            'teams': teams,
            'user_team': user_team
        }
        
        return render(request, 'view_course.html', context)
        
    except Course.DoesNotExist:
        messages.error(request, "Course not found.")
        return redirect('dashboard')

@login_required
def add_teams(request, course_name, course_id):
    """View for adding teams to a course"""
    course = get_object_or_404(Course, id=course_id, name=course_name)
    
    # Check if user is the course creator
    if course.created_by != request.user:
        messages.error(request, "You don't have permission to add teams to this course.")
        return redirect('view_course', course_name=course.name, course_id=course_id)
    
    # Get existing teams for this course
    teams = Team.objects.filter(course=course)
    
    # Get enrolled students who are not yet assigned to a team
    enrolled_students = course.students.all()
    students_on_teams = User.objects.filter(teams__course=course).distinct()
    unassigned_students = enrolled_students.exclude(pk__in=students_on_teams.values_list('pk', flat=True))
    
    context = {
        'course': course,
        'teams': teams,
        'enrolled_students': enrolled_students,
        'unassigned_students': unassigned_students
    }
    
    return render(request, 'add_teams.html', context)

@login_required
def edit_team(request, course_name, team_pk):
    
    team = Team.objects.get(pk=team_pk)
    course = team.course

    course_students = course.students.all()
    students_on_teams = User.objects.filter(teams__course=course).distinct()
    eligible_students = course_students.exclude(pk__in=students_on_teams.values_list('pk', flat=True))

    return render(request, 'edit_team.html', {
        "team": team, "course": course,
        "students": eligible_students,
        "team_members": team.members.all()
    })

@login_required
def delete_team(request, course_name, team_pk):

    team = Team.objects.get(pk=team_pk)
    course = team.course
    team.delete()

    messages.success(request, f"Team deleted successfully.")
    return redirect('view_course', course_name=course_name, course_id=course.pk)

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
    
    # Get courses created by this professor
    courses = Course.objects.filter(created_by=request.user)
    
    # Check if a specific course was requested
    pre_selected_course_id = request.GET.get('course_id')
    
    if request.method == 'POST':
        # Get email addresses from the form
        email_list = request.POST.get('student_emails', '').strip().split('\n')
        email_list = [email.strip() for email in email_list if email.strip()]
        course_id = request.POST.get('course')
        
        # Validate course
        try:
            course = Course.objects.get(pk=course_id)
            # Check if the user is the course creator
            if course.created_by != request.user:
                messages.error(request, "You can only invite students to courses you created.")
                return render(request, 'invite_students.html', {'courses': courses, 'pre_selected_course_id': pre_selected_course_id})
        except Course.DoesNotExist:
            messages.error(request, f"Course not found.")
            return render(request, 'invite_students.html', {'courses': courses, 'pre_selected_course_id': pre_selected_course_id})
        
        # Validate emails
        valid_emails = []
        invalid_emails = []
        already_invited = []
        already_enrolled = []
        
        for email in email_list:
            try:
                validate_email(email)
                # Check if it's a BC email
                if not email.endswith('@bc.edu'):
                    invalid_emails.append(f"{email} (not a BC email)")
                # Check if already enrolled
                elif User.objects.filter(email=email, courses=course).exists():
                    already_enrolled.append(email)
                # Check if already invited
                elif CourseInvitation.objects.filter(email=email, course=course).exists():
                    already_invited.append(email)
                else:
                    valid_emails.append(email)
            except ValidationError:
                invalid_emails.append(f"{email} (invalid format)")
        
        # Process valid emails
        successful_invites = 0
        for email in valid_emails:
            try:
                # Generate a random enrollment code
                enrollment_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                
                # Create invitation
                invitation = CourseInvitation.objects.create(
                    course=course,
                    email=email,
                    invited_by=request.user,
                    enrollment_code=enrollment_code
                )
                
                # Send invitation email
                subject = f"Invitation to join {course.name}"
                message = f"""
                Hello,

                You have been invited by {request.user.get_full_name() or request.user.email} to join the course "{course.name}" ({course.course_code}).

                To accept this invitation, please log in to the Peer Assessment System and use the following enrollment code: {enrollment_code}

                Best regards,
                Peer Assessment System Team
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                
                successful_invites += 1
            except Exception as e:
                messages.error(request, f"Error inviting {email}: {str(e)}")
        
        # Display summary messages
        if successful_invites > 0:
            messages.success(request, f"Successfully sent {successful_invites} invitation(s).")
        
        if invalid_emails:
            messages.warning(request, f"Invalid emails: {', '.join(invalid_emails)}")
        
        if already_invited:
            messages.info(request, f"Already invited: {', '.join(already_invited)}")
        
        if already_enrolled:
            messages.info(request, f"Already enrolled: {', '.join(already_enrolled)}")
        
        # Redirect to course view
        return redirect('view_course', course_id=course.id)
    
    # For GET requests, render the form
    context = {
        'courses': courses,
        'pre_selected_course_id': pre_selected_course_id
    }
    
    return render(request, 'invite_students.html', context)


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
def create_peer_assessments(request):
    """Allow professors to create a single peer assessment with custom questions."""
    if request.user.profile.role != "professor":
        messages.error(request, "Only professors can create peer assessments.")
        return redirect('dashboard')

    if request.method == "POST":
        form = PeerAssessmentForm(request.POST, user=request.user)
        if form.is_valid():
            # Save the assessment first
            assessment = form.save()
            
            # Process Likert questions
            likert_questions = request.POST.getlist('likert_questions[]')
            likert_question_types = request.POST.getlist('likert_question_types[]')
            
            for i, question_text in enumerate(likert_questions):
                if question_text.strip():  # Only save non-empty questions
                    # Get the question type, default to 'team' if not provided
                    question_type = 'team'
                    if i < len(likert_question_types):
                        question_type = likert_question_types[i]
                    
                    LikertQuestion.objects.create(
                        assessment=assessment,
                        question_text=question_text,
                        order=i,
                        question_type=question_type
                    )
            
            # Process open-ended questions
            open_ended_questions = request.POST.getlist('open_ended_questions[]')
            open_ended_question_types = request.POST.getlist('open_ended_question_types[]')
            
            for i, question_text in enumerate(open_ended_questions):
                if question_text.strip():  # Only save non-empty questions
                    # Get the question type, default to 'team' if not provided
                    question_type = 'team'
                    if i < len(open_ended_question_types):
                        question_type = open_ended_question_types[i]
                    
                    OpenEndedQuestion.objects.create(
                        assessment=assessment,
                        question_text=question_text,
                        order=i,
                        question_type=question_type
                    )
            
            messages.success(request, "Peer assessment created successfully with custom questions.")
            return redirect('dashboard')
    else:
        form = PeerAssessmentForm(user=request.user)

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
def enroll_in_course(request):
    if request.method == "POST":
        enrollment_code = request.POST.get("enrollment_code", "").strip()
        
        if enrollment_code:
            try:
                course = Course.objects.get(enrollment_code=enrollment_code)
                course.students.add(request.user)  # Enroll the student
                messages.success(request, f"Successfully enrolled in {course.name}!")
                return redirect('view_course', course_name=course.name, course_id=course.pk)
            except Course.DoesNotExist:
                return render(request, "enroll.html", {"error": "Course not found!"})
        else:
            return render(request, "enroll.html", {"error": "Please provide a course join code."})
    
    return render(request, "enroll.html")


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
    
    # Check if user is a professor and has permission to edit this assessment
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'professor':
        messages.error(request, "Only professors can edit assessment questions.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    if assessment.course.created_by != request.user:
        messages.error(request, "You don't have permission to edit this assessment.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    # Check if assessment is editable
    if not assessment.is_editable:
        messages.error(request, "This assessment is no longer editable.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    # Get existing questions
    likert_questions = LikertQuestion.objects.filter(assessment=assessment).order_by('order')
    open_ended_questions = OpenEndedQuestion.objects.filter(assessment=assessment).order_by('order')
    
    if request.method == 'POST':
        # Check for delete actions first
        if 'delete_likert' in request.POST:
            question_id = request.POST.get('delete_likert')
            try:
                question = LikertQuestion.objects.get(id=question_id, assessment=assessment)
                question.delete()
                messages.success(request, "Likert question deleted successfully.")
                return redirect('edit_assessment_questions', assessment_id=assessment_id)
            except LikertQuestion.DoesNotExist:
                pass
        
        if 'delete_open_ended' in request.POST:
            question_id = request.POST.get('delete_open_ended')
            try:
                question = OpenEndedQuestion.objects.get(id=question_id, assessment=assessment)
                question.delete()
                messages.success(request, "Open-ended question deleted successfully.")
                return redirect('edit_assessment_questions', assessment_id=assessment_id)
            except OpenEndedQuestion.DoesNotExist:
                pass
        
        # Process Likert questions
        likert_count = int(request.POST.get('likert_count', 0))
        for i in range(1, likert_count + 1):
            question_id = request.POST.get(f'likert_id_{i}')
            question_text = request.POST.get(f'likert_text_{i}', '').strip()
            question_order = int(request.POST.get(f'likert_order_{i}', i))
            question_type = request.POST.get(f'likert_type_{i}', 'team')
            
            if not question_text:
                continue  # Skip empty questions
                
            if question_id == 'new':
                # Create new question
                LikertQuestion.objects.create(
                    assessment=assessment,
                    question_text=question_text,
                    order=question_order,
                    question_type=question_type
                )
            else:
                # Update existing question
                try:
                    question = LikertQuestion.objects.get(id=question_id, assessment=assessment)
                    question.question_text = question_text
                    question.order = question_order
                    question.question_type = question_type
                    question.save()
                except LikertQuestion.DoesNotExist:
                    pass
        
        # Process Open-ended questions
        open_ended_count = int(request.POST.get('open_ended_count', 0))
        for i in range(1, open_ended_count + 1):
            question_id = request.POST.get(f'open_ended_id_{i}')
            question_text = request.POST.get(f'open_ended_text_{i}', '').strip()
            question_order = int(request.POST.get(f'open_ended_order_{i}', i))
            question_type = request.POST.get(f'open_ended_type_{i}', 'team')
            
            if not question_text:
                continue  # Skip empty questions
                
            if question_id == 'new':
                # Create new question
                OpenEndedQuestion.objects.create(
                    assessment=assessment,
                    question_text=question_text,
                    order=question_order,
                    question_type=question_type
                )
            else:
                # Update existing question
                try:
                    question = OpenEndedQuestion.objects.get(id=question_id, assessment=assessment)
                    question.question_text = question_text
                    question.order = question_order
                    question.question_type = question_type
                    question.save()
                except OpenEndedQuestion.DoesNotExist:
                    pass
        
        messages.success(request, "Assessment questions updated successfully.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    context = {
        'assessment': assessment,
        'likert_questions': likert_questions,
        'open_ended_questions': open_ended_questions,
    }
    
    return render(request, 'edit_assessment_questions.html', context)

@login_required
def view_team_submissions(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'professor':
        messages.error(request, "Only professors can view team submissions.")
        return redirect('dashboard')
    
    # Get all teams in the course
    teams = Team.objects.filter(course=assessment.course)
    
    # Get selected team if any
    team_id = request.GET.get('team_id')
    selected_team = None
    team_submissions = []
    team_members = []
    submission_matrix = {}
    completed_members = set()
    
    if team_id:
        selected_team = get_object_or_404(Team, id=team_id)
        team_members = list(selected_team.members.all())
        
        # Initialize submission matrix
        for evaluator in team_members:
            submission_matrix[evaluator.id] = {}
            for evaluated in team_members:
                submission_matrix[evaluator.id][evaluated.id] = None
        
        # Get submissions for all team members
        for evaluator in team_members:
            # Get all submissions by this member
            submissions = AssessmentSubmission.objects.filter(
                assessment=assessment,
                student=evaluator.username
            )
            
            # Check if this member has completed all assessments (excluding self)
            if submissions.count() >= len(team_members) - 1:  # Excluding self
                completed_members.add(evaluator.id)
            
            for submission in submissions:
                if submission.assessed_peer:
                    # Add to the matrix
                    submission_matrix[evaluator.id][submission.assessed_peer.id] = submission
                    
                    # Add to the list
                    team_submissions.append({
                        'student': evaluator,
                        'submission': submission,
                        'assessed_peer': submission.assessed_peer,
                        'submission_date': submission.submitted_at
                    })
    
    context = {
        'assessment': assessment,
        'teams': teams,
        'selected_team': selected_team,
        'team_members': team_members,
        'team_submissions': team_submissions,
        'submission_matrix': submission_matrix,
        'completed_members': completed_members,
        'completion_percentage': int(len(completed_members) / len(team_members) * 100) if team_members else 0
    }
    
    return render(request, 'team_submissions.html', context)

@login_required
def fix_session_role(request):
    """Fix the user's session role to match their profile role"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Get or create user profile
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)
    
    # Get current user profile
    current_user = UserProfile.objects.get(user=request.user)
    
    # Update session to match profile role
    request.session['selected_role'] = current_user.role
    request.session['user_role'] = current_user.role
    
    messages.success(request, f'Your role has been synchronized to {current_user.role.title()}')
    
    # Redirect back to dashboard
    return redirect('dashboard')

@login_required
def set_profile_role(request, role):
    """Directly set the user's profile role"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Only allow valid roles
    if role not in ['student', 'professor']:
        messages.error(request, f"Invalid role: {role}")
        return redirect('dashboard')
    
    # Get or create user profile
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)
    
    # Update profile role
    profile = request.user.profile
    profile.role = role
    profile.save()
    
    # Update session to match profile
    request.session['selected_role'] = role
    request.session['user_role'] = role
    
    messages.success(request, f"Profile role updated to: {role}")
    return redirect('dashboard')

@login_required
def submit_student_score(request):
    """API endpoint for professors to submit scores for students"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST requests are allowed'})
    
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'professor':
        return JsonResponse({'success': False, 'error': 'Only professors can submit scores'})
    
    try:
        assessment_id = request.POST.get('assessment_id')
        student_id = request.POST.get('student_id')
        score = request.POST.get('score')
        
        if not all([assessment_id, student_id, score]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        assessment = get_object_or_404(Assessment, id=assessment_id)
        student = get_object_or_404(User, id=student_id)
        
        # Create or update the student score
        student_score, created = StudentScore.objects.update_or_create(
            assessment=assessment,
            student=student,
            defaults={'score': score}
        )
        
        action = 'Created' if created else 'Updated'
        return JsonResponse({
            'success': True, 
            'message': f'{action} score of {score} for {student.get_full_name() or student.username}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def delete_assessment(request, assessment_id):
    """Delete an assessment if the user has permission"""
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if user is a professor and has permission to delete this assessment
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'professor':
        messages.error(request, "Only professors can delete assessments.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    if assessment.course.created_by != request.user:
        messages.error(request, "You don't have permission to delete this assessment.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    # Store course ID for redirection after deletion
    course_id = assessment.course.id
    
    # Delete the assessment
    assessment.delete()
    
    messages.success(request, f"Assessment '{assessment.title}' has been deleted.")
    return redirect('view_course', course_id=course_id)

@login_required
def view_course_invitations(request, course_id):
    """View and manage invitations for a specific course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Check if user is the course creator
    if course.created_by != request.user:
        messages.error(request, "You don't have permission to view invitations for this course.")
        return redirect('view_course', course_id=course_id)
    
    # Get all pending invitations for this course
    invitations = CourseInvitation.objects.filter(course=course, status='pending')
    
    # Handle invitation actions if POST
    if request.method == 'POST':
        action = request.POST.get('action')
        invitation_id = request.POST.get('invitation_id')
        
        if invitation_id and action:
            invitation = get_object_or_404(CourseInvitation, id=invitation_id, course=course)
            
            if action == 'cancel':
                invitation.status = 'cancelled'
                invitation.save()
                messages.success(request, f"Invitation to {invitation.email} has been cancelled.")
            elif action == 'resend':
                # Logic to resend invitation email would go here
                messages.success(request, f"Invitation to {invitation.email} has been resent.")
        
        return redirect('view_course_invitations', course_id=course_id)
    
    context = {
        'course': course,
        'invitations': invitations,
    }
    
    return render(request, 'course_invitations.html', context)

@login_required
def team_dashboard(request):
    """View for displaying all teams the user is a member of or manages"""
    
    # Get user role
    is_professor = (
        hasattr(request.user, 'profile') and 
        request.user.profile.role == 'professor'
    ) or request.session.get('user_role') == 'professor'
    
    if is_professor:
        # For professors, show teams in courses they created
        courses = Course.objects.filter(created_by=request.user)
        teams = Team.objects.filter(course__in=courses)
        
        context = {
            'teams': teams,
            'is_professor': True,
            'courses': courses
        }
    else:
        # For students, show teams they're a member of
        teams = Team.objects.filter(members=request.user)
        
        # Get the courses these teams belong to
        courses = Course.objects.filter(team__in=teams).distinct()
        
        context = {
            'teams': teams,
            'is_professor': False,
            'courses': courses
        }
    
    return render(request, 'team_dashboard.html', context)

@login_required
def edit_course(request, course_id):
    # Get the course using only the ID
    course = get_object_or_404(Course, pk=course_id)
    
    # Check if user is the course creator
    if course.created_by != request.user:
        messages.error(request, "You don't have permission to edit this course.")
        return redirect('view_course', course_name=course.name, course_id=course_id)
    
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        # Validate form data
        if not name:
            messages.error(request, "Course name is required.")
            return render(request, 'edit_course.html', {'course': course})
        
        # Update course
        course.name = name
        course.description = description
        course.save()
        
        messages.success(request, f"Course '{name}' updated successfully.")
        return redirect('view_course', course_name=course.name, course_id=course.id)
    
    # GET request - show edit form
    context = {
        'course': course,
        'edit_mode': True
    }
    
    return render(request, 'edit_course.html', context)

@login_required
def delete_course(request, course_pk):
    """Delete a course if the user has permission"""
    course = get_object_or_404(Course, pk=course_pk)
    
    # Check if user is a professor and has permission to delete this course
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'professor':
        messages.error(request, "Only professors can delete courses.")
        return redirect('view_course', course_id=course_pk)
    
    if course.created_by != request.user:
        messages.error(request, "You don't have permission to delete this course.")
        return redirect('view_course', course_id=course_pk)
    
    # Delete the course
    course_name = course.name
    course.delete()
    
    messages.success(request, f"Course '{course_name}' has been deleted.")
    return redirect('course_dashboard')

@login_required
def view_student_submissions(request, assessment_id):
    """View all student submissions for an assessment"""
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if user is a professor
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'professor':
        messages.error(request, "Only professors can view student submissions.")
        return redirect('dashboard')
    
    # Special case for sample/test data - bypass permission check
    is_sample_data = assessment.title.lower().startswith('sample') or assessment.course.name.lower().startswith('sample')
    
    # Only check permission if it's not sample data
    if not is_sample_data and assessment.course.created_by != request.user:
        messages.error(request, "You don't have permission to view submissions for this assessment.")
        return redirect('dashboard')
    
    # Get student_id from query parameters if provided
    student_id = request.GET.get('student_id')
    selected_student = None
    
    if student_id:
        selected_student = get_object_or_404(User, id=student_id)
        # Get submissions for this specific student
        submissions = AssessmentSubmission.objects.filter(
            assessment=assessment,
            student=selected_student
        )
        
        # If we have a specific student, show their detailed submissions
        context = {
            'assessment': assessment,
            'student': selected_student,
            'submissions': submissions,
        }
        return render(request, 'student_submission_detail.html', context)
    
    # Otherwise, show all submissions grouped by student
    submissions = AssessmentSubmission.objects.filter(assessment=assessment)
    
    # Group submissions by student
    student_submissions = {}
    for submission in submissions:
        if submission.student not in student_submissions:
            student_submissions[submission.student] = []
        student_submissions[submission.student].append(submission)
    
    context = {
        'assessment': assessment,
        'student_submissions': student_submissions,
    }
    
    return render(request, 'student_submissions.html', context)

@login_required
def close_assessment(request, assessment_id):
    """Close an assessment before its deadline"""
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if user is a professor and has permission to close this assessment
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'professor':
        messages.error(request, "Only professors can close assessments.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    if assessment.course.created_by != request.user:
        messages.error(request, "You don't have permission to close this assessment.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    # Check if assessment is already closed
    if assessment.is_closed:
        messages.info(request, f"Assessment '{assessment.title}' is already closed.")
        return redirect('view_assessment', assessment_id=assessment_id)
    
    # Close the assessment
    assessment.is_closed = True
    assessment.closed_date = timezone.now()
    assessment.save()
    
    messages.success(request, f"Assessment '{assessment.title}' has been closed.")
    return redirect('view_assessment', assessment_id=assessment_id)

@login_required
def api_team_submissions(request, team_id, assessment_id):
    """API endpoint to get submission data for a specific team and assessment"""
    # Check if user is a professor
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'professor':
        return JsonResponse({'error': 'Only professors can access this data'}, status=403)
    
    # Get the team and assessment
    team = get_object_or_404(Team, id=team_id)
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Check if professor has permission to view this team's data
    if assessment.course.created_by != request.user:
        return JsonResponse({'error': 'You do not have permission to view this team'}, status=403)
    
    # Get team members
    team_members = list(team.members.all())
    
    # Initialize submission matrix
    submission_matrix = {}
    for evaluator in team_members:
        submission_matrix[evaluator.id] = {}
        for evaluated in team_members:
            submission_matrix[evaluator.id][evaluated.id] = None
    
    # Get all submissions for this team and assessment
    submissions_data = []
    completed_members = set()
    
    for evaluator in team_members:
        # Get all submissions by this member
        submissions = AssessmentSubmission.objects.filter(
            assessment=assessment,
            student=evaluator
        )
        
        # Check if this member has completed all assessments (excluding self)
        if submissions.count() >= len(team_members) - 1:  # Excluding self
            completed_members.add(evaluator.id)
        
        for submission in submissions:
            if submission.assessed_peer:
                # Add to the matrix
                submission_matrix[evaluator.id][submission.assessed_peer.id] = {
                    'id': submission.id,
                    'contribution': submission.contribution,
                    'teamwork': submission.teamwork,
                    'communication': submission.communication,
                    'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None
                }
                
                # Add to the list
                submissions_data.append({
                    'evaluator_id': evaluator.id,
                    'evaluator_name': evaluator.get_full_name() or evaluator.username,
                    'evaluated_id': submission.assessed_peer.id,
                    'evaluated_name': submission.assessed_peer.get_full_name() or submission.assessed_peer.username,
                    'submission_id': submission.id,
                    'contribution': submission.contribution,
                    'teamwork': submission.teamwork,
                    'communication': submission.communication,
                    'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None
                })
    
    # Calculate completion percentage
    completion_percentage = int(len(completed_members) / len(team_members) * 100) if team_members else 0
    
    return JsonResponse({
        'team': {
            'id': team.id,
            'name': team.name or f"Team {team.id}"
        },
        'assessment': {
            'id': assessment.id,
            'title': assessment.title
        },
        'team_members': [
            {
                'id': member.id,
                'name': member.get_full_name() or member.username,
                'username': member.username,
                'completed': member.id in completed_members
            } for member in team_members
        ],
        'submission_matrix': submission_matrix,
        'submissions': submissions_data,
        'completion_percentage': completion_percentage
    })

def about(request):
    """View for the About page"""
    return render(request, 'about.html')
