from celery import shared_task
from django.utils.timezone import now, timedelta
from assessments.models import Assessment
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from assessments.models import Submission

@shared_task
def peer_assessment_due_date_reminder():

    start_window = now() + timedelta(minutes=1) # set to 1 minutes and 5 minutes for testing purposes
    end_window = now() + timedelta(minutes=5)

    assessments = Assessment.objects.filter(
        due_date__gte = start_window,
        due_date__lte = end_window,
        reminder_sent = False
    )

    for assessment in assessments:
        course = assessment.course
        students = course.students.all()

        for student in students:

            subject = f"Reminder: {assessment.title} Is Due Soon!"
            message = (
                f"Dear {student.get_full_name()},\n\n"
                f"{assessment.title} is due at {assessment.due_date.strftime('%Y-%m-%d %I:%M %p')}.\n" 
                f"Please make sure to complete an assessment for each member of your team before the assignment closes!\n\n"
                f"Best,\n" 
                f"The PeerAssess Team"
            )

            send_mail(
               subject,
               message,
               settings.DEFAULT_FROM_EMAIL,
               [student.email],
               fail_silently=False
            )

        assessment.reminder_sent = True
        assessment.save()
        
@shared_task
def send_assignment_survey_email(subject, message, recipient_list):
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

@shared_task
def close_assessment():

    assessments = Assessment.objects.filter(
        due_date__lte = now(),
        is_closed = False
    )

    for assessment in assessments:
        assessment.closed_date = now()
        assessment.is_closed = True
        assessment.save()

@shared_task
def send_submission_verification_email(submission_id):
    sub = Submission.objects.get(pk=submission_id)
    if sub.is_verified:
        return

    verify_url = settings.SITE_URL + reverse("verify_submission") + f"?token={sub.verification_token}"
    subject = "Please verify your submission"
    html_body = render_to_string("emails/submission_verification.html", {
        "user": sub.user,
        "verify_url": verify_url,
        "expires_at": sub.token_expires_at,
    })

    send_mail(
        subject,
        "",  # plaintext fallback
        settings.DEFAULT_FROM_EMAIL,
        [sub.user.email],
        html_message=html_body,
        fail_silently=False,
    )