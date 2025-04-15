from celery import shared_task
from django.utils.timezone import now, timedelta
from assessments.models import Assessment
from django.core.mail import send_mail
from django.conf import settings

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
