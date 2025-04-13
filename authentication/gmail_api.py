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
        logger.debug(f"Looking for Google account for user {user.email}")
        social_account = SocialAccount.objects.get(user=user, provider='google')
        logger.debug(f"Found Google account: {social_account.uid}")
        
        # Get the access token
        logger.debug(f"Looking for token for account {social_account.id}")
        try:
            token = SocialToken.objects.get(account=social_account)
            logger.debug(f"Found token: {token.token[:10]}...")
            logger.debug(f"Has refresh token: {bool(token.token_secret)}")
        except SocialToken.DoesNotExist:
            logger.error(f"No token found for user {user.email}. User needs to re-authenticate.")
            return None
        
        # Check if we have a refresh token
        if not token.token_secret:
            logger.error("No refresh token found. User needs to re-authenticate.")
            return None
        
        # Get the client ID and secret from the SocialApp
        from allauth.socialaccount.models import SocialApp
        social_app = SocialApp.objects.get(provider='google')
        
        # Create credentials
        credentials = Credentials(
            token=token.token,
            refresh_token=token.token_secret,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=social_app.client_id,
            client_secret=social_app.secret,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        
        # Build the Gmail service
        logger.debug("Building Gmail service")
        service = build('gmail', 'v1', credentials=credentials)
        logger.debug("Gmail service built successfully")
        return service
    
    except SocialAccount.DoesNotExist:
        logger.error(f"No Google account found for user {user.email}. User needs to connect their Google account.")
        return None
    except Exception as e:
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