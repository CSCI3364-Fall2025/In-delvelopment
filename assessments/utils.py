from django.core.mail import send_mail
from django.conf import settings

def send_assessment_publication_email(student_email, assessment):
    subject = f"Peer Assessment '{assessment.title}' is now open!"
    message = (
        f"Dear Student,\n\n"
        f"The peer assessment '{assessment.title}' is now open and will close at {assessment.closing_date}.\n\n"
        f"Best regards,\nCourse Team"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [student_email])

def send_assessment_warning_email(student_email, assessment, hours_left):
    subject = f"Reminder: Peer Assessment '{assessment.title}' closing soon!"
    message = (
        f"Dear Student,\n\n"
        f"Our records show that you haven’t submitted your response for the peer assessment '{assessment.title}'.\n"
        f"The assessment will close in {hours_left} hours (closing at {assessment.closing_date}). Please complete it soon.\n\n"
        f"Best regards,\nCourse Team"
    )
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [student_email])
