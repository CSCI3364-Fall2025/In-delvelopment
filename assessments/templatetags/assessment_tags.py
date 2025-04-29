from django import template
from assessments.models import LikertResponse, OpenEndedResponse
from django.contrib.auth.models import User

register = template.Library()

@register.simple_tag
def has_response_with_rating_for_teammate(submission, question, teammate, rating):
    """Check if a submission has a response with the given rating for a specific teammate"""
    if not submission:
        return False
    
    try:
        response = LikertResponse.objects.get(
            submission=submission,
            question=question,
            teammate=teammate
        )
        return response.rating == rating
    except LikertResponse.DoesNotExist:
        return False

@register.simple_tag
def get_open_ended_response_for_teammate(submission, question, teammate):
    """Get the open-ended response text for a specific teammate"""
    if not submission:
        return ""
    
    try:
        response = OpenEndedResponse.objects.get(
            submission=submission,
            question=question,
            teammate=teammate
        )
        return response.response_text
    except OpenEndedResponse.DoesNotExist:
        return ""

@register.simple_tag
def get_open_ended_response(submission, question):
    """Get the open-ended response text for a team question"""
    if not submission:
        return ""
    
    try:
        response = OpenEndedResponse.objects.get(
            submission=submission,
            question=question,
            teammate=None
        )
        return response.response_text
    except OpenEndedResponse.DoesNotExist:
        return "" 