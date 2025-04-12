from django.core.mail.backends.base import BaseEmailBackend
from django.contrib.auth import get_user_model
from django.conf import settings
from .gmail_api import send_email_via_gmail
import logging

logger = logging.getLogger(__name__)

class GmailAPIEmailBackend(BaseEmailBackend):
    """
    Custom email backend that uses the Gmail API.
    Falls back to the configured Django email backend if Gmail API is not available.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.fail_silently = fail_silently
        
        # Import the fallback backend
        from django.core.mail.backends.console import EmailBackend
        self.fallback_backend = EmailBackend(fail_silently=fail_silently)
    
    def send_messages(self, email_messages):
        """
        Send email messages using the Gmail API if possible,
        otherwise fall back to the standard backend.
        """
        if not email_messages:
            return 0
            
        # Check if we should use the Gmail API
        if not getattr(settings, 'USE_GMAIL_API', False):
            return self.fallback_backend.send_messages(email_messages)
            
        # Try to find a professor user to send emails
        User = get_user_model()
        professors = User.objects.filter(profile__role='professor')
        
        if not professors.exists():
            logger.warning("No professor users found to send emails via Gmail API")
            return self.fallback_backend.send_messages(email_messages)
            
        # Use the first professor's account to send emails
        sender = professors.first()
        
        count = 0
        for message in email_messages:
            for recipient in message.to:
                if send_email_via_gmail(
                    user=sender,
                    to=recipient,
                    subject=message.subject,
                    body=message.body
                ):
                    count += 1
                elif not self.fail_silently:
                    raise Exception(f"Failed to send email to {recipient}")
                    
        return count 