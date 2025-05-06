from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.db.models.signals import pre_save
from django.db.models.signals import post_save
from django.dispatch import receiver
from assessments.models import Assessment, User, Course
from django.core.mail import send_mail
from django.conf import settings
from assessments.models import Submission
from .tasks import send_submission_verification_email
from authentication.models import UserProfile

@receiver(user_signed_up)
def set_user_role(sender, request, user, **kwargs):
    """Set the user role when a user signs up"""
    # Get the role from session
    selected_role = request.session.get('user_role', 'student')
    
    # Update the user's profile with the selected role
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.role = selected_role
    profile.save()
    
    # Clear the session variable
    if 'user_role' in request.session:
        del request.session['user_role']
        
        
@receiver(pre_save, sender=Assessment)
def send_assignment_published_email(sender, instance, **kwargs):
    """
    Sends an email to students when an assignment (Assessment) is published.
    This signal expects the Assessment model to have a Boolean field 'published'.
    """
    if instance.pk:
        previous = Assessment.objects.get(pk=instance.pk)
        if not previous.results_published and instance.results_published:
            student_emails = list(User.objects.filter(is_staff=False, is_active=True)
                                  .values_list('email', flat=True))
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