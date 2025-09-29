from django.contrib.auth import get_user_model
from .models import Course, Assessment
import pytest

from django.utils import timezone

@pytest.mark.django_db
def test_course_str_includes_code_and_name():
    ## Test that the Course model's __str__ method returns the expected format.
    instructor = get_user_model().objects.create_user(
        username="instructor",
        email="instructor@example.com",
        password="password",
    )

    course = Course.objects.create(
        name="Software Testing",
        course_code="TEST101",
        year="2024",
        semester="Fall",
        description="Intro course",
        created_by=instructor,
    )

    assert str(course) == "TEST101: Software Testing"

def test_assessment_returns_title():
    ## Test that the Assessment model's __str__ method returns the assessment title.
    a = Assessment()
    a.title = "Midterm Peer Review"
    assert str(a) == "Midterm Peer Review"

def test_assessment_is_scheduled():
    ## Test that the Assessment model correctly identifies when an assessment is scheduled.
    a = Assessment()
    a.is_published = True
    a.release_date = timezone.now() + timezone.timedelta(days=2)
    assert a.is_scheduled is True