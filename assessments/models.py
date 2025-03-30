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

class Team(models.Model):
    name = models.CharField(max_length=50, blank=True)
    members = models.ManyToManyField(User, related_name="teams", blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Team {self.pk if len(self.name) == 0 else self.name}"
        
class Course(models.Model):
    name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=10)
    year = models.CharField(max_length=4, blank=True)
    semester = models.CharField(max_length=6, blank=True)
    description = models.TextField(max_length=500)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_courses")
    teams = models.ManyToManyField(Team, related_name="course", blank=True)
    students = models.ManyToManyField(User, related_name="courses", blank=True)
    assessments = models.ManyToManyField(Assessment, related_name="associated_course", blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.course_code}: {self.name}"

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
