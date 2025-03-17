from django.db import models
from django.contrib.auth.models import User

class Assessment(models.Model):
    title = models.CharField(max_length=255)
    course = models.CharField(max_length=255)
    due_date = models.DateTimeField()
    closed_date = models.DateTimeField(null=True, blank=True)
    open_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class AssessmentSubmission(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    student = models.CharField(max_length=255)
    contribution = models.IntegerField()
    teamwork = models.IntegerField()
    communication = models.IntegerField()
    feedback = models.TextField()

    def __str__(self):
        return f"{self.assessment.title} - {self.student}"
