import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from allauth.socialaccount.models import SocialToken, SocialAccount
import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings
import os
import json

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

class GmailAPIBackend(BaseEmailBackend):
    """
    A Django email backend that uses the Gmail API.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.fail_silently = fail_silently
        
    def send_messages(self, email_messages):
        """
        Send email messages using the Gmail API.
        """
        if not email_messages:
            return 0
            
        count = 0
        
        try:
            # Get credentials from token file
            token_file = settings.GOOGLE_OAUTH2_TOKEN_JSON
            client_secrets_file = settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON
            
            if not os.path.exists(token_file):
                logger.error(f"Token file not found: {token_file}")
                if not self.fail_silently:
                    raise FileNotFoundError(f"Token file not found: {token_file}")
                return 0
                
            if not os.path.exists(client_secrets_file):
                logger.error(f"Client secrets file not found: {client_secrets_file}")
                if not self.fail_silently:
                    raise FileNotFoundError(f"Client secrets file not found: {client_secrets_file}")
                return 0
            
            # Load client secrets
            with open(client_secrets_file, 'r') as f:
                client_config = json.load(f)
                
            client_id = client_config['web']['client_id']
            client_secret = client_config['web']['client_secret']
            
            # Load token
            with open(token_file, 'r') as f:
                token_data = json.load(f)
            
            # Create credentials
            credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret,
                scopes=settings.GMAIL_API_SCOPES
            )
            
            # Build the Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            
            # Send each message
            for message in email_messages:
                try:
                    # Create the email
                    email = MIMEText(message.body)
                    email['to'] = ', '.join(message.to)
                    email['subject'] = message.subject
                    email['from'] = message.from_email or settings.DEFAULT_FROM_EMAIL
                    
                    # Add CC recipients if any
                    if message.cc:
                        email['cc'] = ', '.join(message.cc)
                    
                    # Add BCC recipients if any
                    if message.bcc:
                        email['bcc'] = ', '.join(message.bcc)
                    
                    # Encode the message
                    raw_message = base64.urlsafe_b64encode(email.as_bytes()).decode('utf-8')
                    
                    # Send the message
                    sent_message = service.users().messages().send(
                        userId='me', 
                        body={'raw': raw_message}
                    ).execute()
                    
                    logger.info(f"Email sent via Gmail API, message ID: {sent_message.get('id')}")
                    count += 1
                    
                    # Update token file with new access token if refreshed
                    if credentials.token != token_data.get('token'):
                        token_data['token'] = credentials.token
                        with open(token_file, 'w') as f:
                            json.dump(token_data, f)
                        
                except Exception as e:
                    logger.error(f"Error sending email via Gmail API: {str(e)}")
                    if not self.fail_silently:
                        raise
            
            return count
            
        except Exception as e:
            logger.error(f"Error initializing Gmail API: {str(e)}")
            if not self.fail_silently:
                raise
            return 0 