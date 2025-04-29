import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone #for updates
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
from django.conf import settings
from django.db import models


class Course(models.Model):
    name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=10)
    year = models.CharField(max_length=4, blank=True)
    semester = models.CharField(max_length=6, blank=True)
    description = models.TextField(max_length=500)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_courses")
    students = models.ManyToManyField(User, related_name="courses", blank=True)
    is_active = models.BooleanField(default=True)
    enrollment_code = models.CharField(max_length=8, unique=True, null=True, blank=True, editable=False)

    def __str__(self):
        return f"{self.course_code}: {self.name}"    

class Assessment(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assessments")
    due_date = models.DateTimeField(null=True, blank=True)
    closed_date = models.DateTimeField(null=True, blank=True)
    open_date = models.DateTimeField(null=True, blank=True)
    self_assessment_required = models.BooleanField(default=False)  # New field
    results_published = models.BooleanField(default=False)
    published_date = models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)
    release_date = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)

    def __str__(self):
        return self.title
        
    def publish(self):
        self.published = True
        self.publish_date = timezone.now()
        self.save()

    def publish_now(self):
        """Publish the assessment immediately"""
        self.release_date = timezone.now()
        self.is_published = True
        self.save()

    @property
    def is_editable(self):
        """
        Assessment is editable if it's not published yet and not active
        (or if release_date is None)
        """
        if not self.is_published:
            if self.release_date is None:
                return True
            return timezone.now() < self.release_date
        return False

    @property
    def is_scheduled(self):
        """Check if the assessment is published but scheduled for future release"""
        return (self.is_published and 
                self.release_date is not None and 
                self.release_date > timezone.now())

class Team(models.Model):
    name = models.CharField(max_length=50, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="teams", default=None)
    members = models.ManyToManyField(User, related_name="teams", blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Team {self.pk if len(self.name) == 0 else self.name}"

class AssessmentScore(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scores")
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="scores")
    score = models.FloatField()

class AssessmentSubmission(models.Model):
    assessment = models.ForeignKey('Assessment', on_delete=models.CASCADE, related_name='submissions')
    student = models.CharField(max_length=150)  # Username of the person submitting
    assessed_peer = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='assessed_submissions')
    contribution = models.IntegerField()
    teamwork = models.IntegerField()
    communication = models.IntegerField()
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} → {self.assessed_peer.username} | {self.assessment.title}"

    class Meta:
        unique_together = ['assessment', 'student']  # One submission per student per assessment

    def __str__(self):
        return f"{self.assessment.title} - {self.student}"
        
class PeerAssessment(models.Model):
    title = models.CharField(max_length=255)
    publication_date = models.DateTimeField()
    closing_date = models.DateTimeField()
    publication_email_sent = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

class CourseInvitation(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_invitations")
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    enrollment_code = models.CharField(max_length=8, unique=True, null=True, blank=True)
    
    class Meta:
        unique_together = ['course', 'email']
        
    def __str__(self):
        return f"Invitation to {self.course.name} for {self.email}"

class LikertQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('team', 'Team Question (Overall)'),
        ('individual', 'Individual Question (Per Teammate)'),
    ]
    
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='likert_questions')
    question_text = models.CharField(max_length=500)  # Match existing field type
    order = models.IntegerField(default=0)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='team')
    
    def __str__(self):
        if len(self.question_text) > 30:
            return f"{self.question_text[:30]}..."
        return self.question_text

class OpenEndedQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('team', 'Team Question (Overall)'),
        ('individual', 'Individual Question (Per Teammate)'),
    ]
    
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='open_ended_questions')
    question_text = models.CharField(max_length=500)  # Match existing field type
    order = models.IntegerField(default=0)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='team')
    
    def __str__(self):
        if len(self.question_text) > 30:
            return f"{self.question_text[:30]}..."
        return self.question_text

class LikertResponse(models.Model):
    submission = models.ForeignKey('AssessmentSubmission', on_delete=models.CASCADE, related_name='likert_responses')
    question = models.ForeignKey(LikertQuestion, on_delete=models.CASCADE)
    rating = models.IntegerField()
    teammate = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, 
                                related_name='likert_evaluations')
    
    class Meta:
        unique_together = ('submission', 'question', 'teammate')
        
    def __str__(self):
        if self.teammate:
            return f"Response to {self.question} for {self.teammate.username}: {self.rating}"
        return f"Response to {self.question}: {self.rating}"

class OpenEndedResponse(models.Model):
    submission = models.ForeignKey('AssessmentSubmission', on_delete=models.CASCADE, related_name='open_ended_responses')
    question = models.ForeignKey(OpenEndedQuestion, on_delete=models.CASCADE)
    response_text = models.TextField()
    teammate = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='open_ended_evaluations')
    
    class Meta:
        unique_together = ('submission', 'question', 'teammate')
    
    def __str__(self):
        if self.teammate:
            return f"Response to {self.question} for {self.teammate.username}"
        return f"Response to {self.question}"

class StudentScore(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'assessment')

def default_val():
    return timezone.now() + timedelta(hours=24)

class Submission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # ─── Verification fields ───────────────────────
    is_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )
    
    token_expires_at = models.DateTimeField(
        default = default_val
    )

    def mark_verified(self):
        self.is_verified = True
        self.verification_token = None
        self.token_expires_at = None
        self.save()
