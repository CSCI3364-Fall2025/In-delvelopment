from django.db import models
from django.contrib.auth.models import User

class Assessment(models.Model):
    title = models.CharField(max_length=200)
    course = models.CharField(max_length=100)
    due_date = models.DateTimeField(null=True, blank=True)
    closed_date = models.DateTimeField(null=True, blank=True)
    open_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title
        
class AssessmentScore(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scores")
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="scores")
    score = models.FloatField()

class AssessmentSubmission(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    student = models.CharField(max_length=255)
    contribution = models.IntegerField()
    teamwork = models.IntegerField()
    communication = models.IntegerField()
    feedback = models.TextField()

    def __str__(self):
        return f"{self.assessment.title} - {self.student}"
