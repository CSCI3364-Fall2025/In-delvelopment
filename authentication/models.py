from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from assessments.models import Assessment

# Create your models here.

class UserProfile(models.Model):
    USER_ROLES = (
        ('student', 'Student'),
        ('professor', 'Professor'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=USER_ROLES, default='student')
    preferred_name = models.CharField(max_length=50, null=True, blank=True)
    progress_data = models.JSONField(default=dict)  # Store progress as JSON

    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"

class AssessmentProgress(models.Model):
    
    def default_progress_notes(): # So that you can migrate without any issues
        return {}

    student = models.ForeignKey(User, on_delete=models.CASCADE)  # Link to the user
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)  # Link to the assessment
    progress_notes = models.JSONField(default=default_progress_notes)  # Store progress as JSON
    last_updated = models.DateTimeField(auto_now=True)  # Auto-update timestamp

    def __str__(self):
        return f"{self.student.username} - {self.assessment.title} Progress"


# Signal to create/update UserProfile when User is created/updated
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()
