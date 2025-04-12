import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from allauth.socialaccount.models import SocialToken, SocialAccount
import logging

logger = logging.getLogger(__name__)

def get_gmail_service(user):
    """
    Get a Gmail API service instance for a user.
    
    Args:
        user: The Django user object
    
    Returns:
        A Gmail API service instance or None if not possible
    """
    try:
        # Get the user's Google social account
        social_account = SocialAccount.objects.get(user=user, provider='google')
        
        # Get the access token
        token = SocialToken.objects.get(account=social_account)
        
        # Create credentials
        credentials = Credentials(
            token=token.token,
            refresh_token=token.token_secret,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=social_account.provider_client_id,
            client_secret=social_account.provider_client_secret,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        
        # Build the Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        return service
    
    except (SocialAccount.DoesNotExist, SocialToken.DoesNotExist) as e:
        logger.error(f"Failed to get Gmail service for user {user.email}: {str(e)}")
        return None

def send_email_via_gmail(user, to, subject, body):
    """
    Send an email using the Gmail API.
    
    Args:
        user: The Django user sending the email
        to: Recipient email address
        subject: Email subject
        body: Email body text
    
    Returns:
        Boolean indicating success or failure
    """
    try:
        service = get_gmail_service(user)
        if not service:
            logger.error(f"Could not get Gmail service for {user.email}")
            return False
        
        # Create the email message
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        message['from'] = user.email
        
        # Encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send the message
        message_object = {'raw': raw_message}
        sent_message = service.users().messages().send(userId='me', body=message_object).execute()
        
        logger.info(f"Email sent to {to}, message ID: {sent_message.get('id')}")
        return True
    
    except Exception as e:
        logger.error(f"Error sending email via Gmail API: {str(e)}")
        return False 