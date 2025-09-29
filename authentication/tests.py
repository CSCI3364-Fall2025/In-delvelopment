from django.test import TestCase

# Create your tests here.
import pytest
from django.contrib.auth import get_user_model
from authentication.models import UserProfile, AssessmentProgress
from assessments.models import Course, Assessment

@pytest.mark.django_db
def test_user_profile_str_uses_email_and_role():

    '''reasoning: the UserProfile.__str__ should return the user's email and role
    (e.g. "alice@example.com - Student"), so we create a predictable user here to
    assert that behavior.'''
    
    user = get_user_model().objects.create_user(
        username="alice",
        email="alice@example.com",
        password="password123",
    )
    profile = UserProfile.objects.get(user=user)

    assert str(profile) == "alice@example.com - Student"

@pytest.mark.django_db
def test_assessment_progress_str_joins_student_and_assessment():

    '''reasoning: the AssessmentProgress.__str__ should join the student's username
    and the assessment title (e.g. "charlie - Project 1 Progress"), so we create a
    predictable user here to assert that behavior.'''

    user = get_user_model().objects.create_user(
        username="charlie",
        email="charlie@example.com",
        password="secret",
    )
    course = Course.objects.create(
        name="Software Testing",
        course_code="TEST101",
        year="2024",
        semester="Fall",
        description="Intro course",
        created_by=user,
    )
    assessment = Assessment.objects.create(title="Project 1", course=course)
    progress = AssessmentProgress.objects.create(student=user, assessment=assessment)

    assert str(progress) == "charlie - Project 1 Progress"