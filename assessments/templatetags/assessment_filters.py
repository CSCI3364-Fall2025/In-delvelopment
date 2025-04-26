from django import template

register = template.Library()

@register.filter
def range_filter(num):
    """Returns a range from 1 to num (inclusive)"""
    return range(1, int(num) + 1)

@register.filter
def filter_by_question_rating(responses, args):
    """
    Filter responses by question and rating
    Usage: submission.likert_responses.all|filter_by_question_rating:question,rating
    """
    args_list = args.split(',')
    if len(args_list) != 2:
        return False
    
    question, rating = args_list
    
    # Convert rating to int if it's a string
    if isinstance(rating, str):
        rating = int(rating)
        
    for response in responses:
        if response.question == question and response.rating == rating:
            return True
    return False

@register.simple_tag
def has_response_with_rating(submission, question, rating):
    """
    Check if a submission has a response for a specific question with a specific rating
    Usage: {% has_response_with_rating submission question rating as has_response %}
    """
    if not submission:
        return False
    
    return submission.likert_responses.filter(question=question, rating=rating).exists()

@register.simple_tag
def get_open_ended_response(submission, question):
    """
    Get the response text for an open-ended question
    Usage: {% get_open_ended_response submission question as response_text %}
    """
    if not submission:
        return ''
    
    response = submission.open_ended_responses.filter(question=question).first()
    return response.response_text if response else ''
