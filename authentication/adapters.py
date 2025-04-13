from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from allauth.account.utils import user_email, user_username, user_field
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
import logging

logger = logging.getLogger(__name__)

class BCEmailAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """Validate that the email is from BC domain"""
        # Get email from the social account data
        email = sociallogin.account.extra_data.get('email', '')
        
        # Check if email is present (Google should provide it)
        if not email:
            messages.error(request, "Could not retrieve email from your Google account.")
            return HttpResponseRedirect('/login-error/?error=no_email')
            
        # Check if email is from BC domain
        if not email.endswith('@bc.edu'):
            # Clear any existing success messages
            storage = messages.get_messages(request)
            for message in storage:
                # Remove any success messages
                if message.level == messages.SUCCESS:
                    storage.used = True
            
            messages.error(request, "Only Boston College (@bc.edu) email addresses are allowed.")
            # Redirect to a custom error page instead of raising an exception
            return HttpResponseRedirect('/login-error/?error=non_bc_email&email=' + email)
        
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
    
    def save_token(self, socialtoken):
        """Ensure refresh token is saved properly"""
        logger.debug(f"Saving token for user: {socialtoken.account.user.email}")
        logger.debug(f"Token: {socialtoken.token[:10]}...")
        logger.debug(f"Refresh token exists: {bool(socialtoken.token_secret)}")
        
        # Make sure to call the parent method to save the token
        super().save_token(socialtoken)
    
    def parse_token(self, data, token):
        """Make sure refresh token is properly parsed from OAuth response"""
        token = super().parse_token(data, token)
        
        # Log the token data for debugging
        logger.debug(f"OAuth token data keys: {data.keys()}")
        logger.debug(f"OAuth token data: {data}")
        
        # Check if we have a refresh token in the data
        if 'refresh_token' in data:
            token.token_secret = data['refresh_token']
            logger.debug(f"Parsed refresh token: {token.token_secret[:5]}...")
        else:
            logger.warning("No refresh token in OAuth response - user won't be able to use Gmail API")
            logger.warning("This usually happens when the user has already granted access")
            logger.warning("User should revoke access at https://myaccount.google.com/permissions")
            
        return token
    
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