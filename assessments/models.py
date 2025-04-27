from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone #for updates


class Course(models.Model):
    name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=10)
    year = models.CharField(max_length=4, blank=True)
    semester = models.CharField(max_length=6, blank=True)
    description = models.TextField(max_length=500)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_courses")
    students = models.ManyToManyField(User, related_name="courses", blank=True)
    is_active = models.BooleanField(default=True)

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

    def __str__(self):
        return self.title
        
    def publish(self):
        self.published = True
        self.publish_date = timezone.now()
        self.save()

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
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='likert_questions')
    question_text = models.CharField(max_length=500)
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return self.question_text
        
class OpenEndedQuestion(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='open_ended_questions')
    question_text = models.CharField(max_length=500)
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return self.question_text

class LikertResponse(models.Model):
    submission = models.ForeignKey('AssessmentSubmission', on_delete=models.CASCADE, related_name='likert_responses')
    question = models.ForeignKey(LikertQuestion, on_delete=models.CASCADE)
    rating = models.IntegerField()
    
    class Meta:
        unique_together = ['submission', 'question']
        
class OpenEndedResponse(models.Model):
    submission = models.ForeignKey('AssessmentSubmission', on_delete=models.CASCADE, related_name='open_ended_responses')
    question = models.ForeignKey(OpenEndedQuestion, on_delete=models.CASCADE)
    response_text = models.TextField()
    
    class Meta:
        unique_together = ['submission', 'question']
