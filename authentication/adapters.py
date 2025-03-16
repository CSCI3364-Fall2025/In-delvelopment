from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from allauth.account.utils import user_email, user_username, user_field

class BCEmailAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Validate that the email is from BC domain"""
        # Get email from the social account data
        email = sociallogin.account.extra_data.get('email', '')
        
        # Check if email is present (Google should provide it)
        if not email:
            messages.error(request, "Could not retrieve email from your Google account.")
            return redirect('login')
            
        # Check if email is from BC domain
        if not email.endswith('@bc.edu'):
            messages.error(request, "Only Boston College (@bc.edu) email addresses are allowed.")
            # Prevent the login
            return redirect('login')
        
        # Get the role from session
        selected_role = request.session.get('selected_role', 'student')
        # Store it for later use
        request.session['user_role'] = selected_role
        
        # Auto-connect accounts with the same email address
        if not sociallogin.is_existing:
            # Check if we already have a user with this email
            try:
                user = self.get_user_by_email(email)
                sociallogin.connect(request, user)
            except:
                pass
    
    def save_user(self, request, sociallogin, form=None):
        """Save the user and set their role"""
        user = super().save_user(request, sociallogin, form)
        
        # Set the user's role based on what was selected
        selected_role = request.session.get('user_role', 'student')
        if hasattr(user, 'profile'):
            profile = user.profile
            profile.role = selected_role
            profile.save()
            
        return user
        
    def get_user_by_email(self, email):
        """Get a user by email address"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.get(email=email) 