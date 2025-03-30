from django import template

register = template.Library()

@register.filter
def range_filter(value):
    """Generate a range of numbers from 1 to the given value (inclusive)."""
    return range(1, value + 1)
