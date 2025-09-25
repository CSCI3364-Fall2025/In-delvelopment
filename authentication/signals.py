from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from assessments.models import Assessment, Submission, User
from .tasks import send_submission_verification_email
from .models import UserProfile


@receiver(pre_save, sender=Assessment)
def send_assignment_published_email(sender, instance, **kwargs):
    """Notify active students when assessment results are published."""
    if instance.pk:
        previous = Assessment.objects.get(pk=instance.pk)
        if not previous.results_published and instance.results_published:
            student_emails = list(
                User.objects.filter(is_staff=False, is_active=True).values_list('email', flat=True)
            )
            if student_emails:
                subject = f"New Assignment Published: {instance.title}"
                message = (
                    f"Dear Student,\n\n"
                    f"A new assignment titled '{instance.title}' has been published. "
                    "Please log in to your account to view the details and submit your work.\n\n"
                    "Best regards,\nYour Course Team"
                )
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, student_emails)


@receiver(post_save, sender=Submission)
def send_verification_on_create(sender, instance, created, **kwargs):
    if created and not instance.is_verified:
        send_submission_verification_email.delay(instance.id)


@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
