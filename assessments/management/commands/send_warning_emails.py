from django.core.management.base import BaseCommand
from django.utils import timezone
from assessments.models import PeerAssessment, Submission
from django.contrib.auth.models import User  # or your custom user model
from assessments.utils import send_assessment_warning_email

class Command(BaseCommand):
    help = 'Send warning emails to students with pending submissions for assessments nearing closure.'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        # Get all assessments that haven't closed yet
        assessments = PeerAssessment.objects.filter(closing_date__gt=now)
        for assessment in assessments:
            time_left = assessment.closing_date - now
            hours_left = time_left.total_seconds() / 3600

            # If the closing time is about 12 or 24 hours away
            if 11.5 <= hours_left <= 12.5 or 23.5 <= hours_left <= 24.5:
                # For each student, check if they have NOT submitted
                students = User.objects.all()  # or filter to enrolled students
                for student in students:
                    if not Submission.objects.filter(
                        assessment=assessment, 
                        student=student
                    ).exists():
                        send_assessment_warning_email(student.email, assessment, round(hours_left, 1))
                        self.stdout.write(self.style.SUCCESS(
                            f"Sent warning email to {student.email} for assessment '{assessment.title}'"
                        ))
