from django.core.management.base import BaseCommand
from django.utils import timezone
from assessments.models import PeerAssessment
from django.contrib.auth.models import User  # or your custom user model
from assessments.utils import send_assessment_publication_email

class Command(BaseCommand):
    help = 'Send publication emails for assessments that are now open.'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        # Get assessments where publication date has passed and the email hasn't been sent yet.
        assessments = PeerAssessment.objects.filter(
            publication_date__lte=now, 
            publication_email_sent=False
        )
        for assessment in assessments:
            students = User.objects.all()  # or filter to enrolled students
            for student in students:
                send_assessment_publication_email(student.email, assessment)
                self.stdout.write(self.style.SUCCESS(
                    f"Sent publication email to {student.email} for assessment '{assessment.title}'"
                ))
            assessment.publication_email_sent = True
            assessment.save()
