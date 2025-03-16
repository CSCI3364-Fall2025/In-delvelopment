from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from .models import UserProfile

@receiver(user_signed_up)
def set_user_role(sender, request, user, **kwargs):
    """Set the user role when a user signs up"""
    # Get the role from session
    selected_role = request.session.get('user_role', 'student')
    
    # Update the user's profile with the selected role
    if hasattr(user, 'profile'):
        profile = user.profile
        profile.role = selected_role
        profile.save()
        
    # Clear the session variable
    if 'user_role' in request.session:
        del request.session['user_role'] 