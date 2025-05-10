from django.core.management.base import BaseCommand
import json
import os
from django.conf import settings
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pathlib import Path

class Command(BaseCommand):
    help = 'Set up Gmail API credentials and generate token file'

    def add_arguments(self, parser):
        parser.add_argument('--client-secrets', type=str, help='Path to client secrets JSON file')
        parser.add_argument('--token-file', type=str, help='Path to save token JSON file')
        parser.add_argument('--port', type=int, default=8080, help='Port for OAuth callback server')

    def handle(self, *args, **options):
        self.stdout.write('Setting up Gmail API credentials...')
        
        # Get file paths from arguments or settings
        client_secrets_file = options.get('client_secrets')
        token_file = options.get('token_file')
        port = options.get('port')
        
        if not client_secrets_file:
            try:
                client_secrets_file = settings.GOOGLE_OAUTH2_CLIENT_SECRETS_JSON
            except AttributeError:
                # If setting is not available, use default path
                client_secrets_file = Path(__file__).resolve().parent.parent.parent.parent / "google_oauth_client.json"
                self.stdout.write(f"Using default client secrets path: {client_secrets_file}")
        
        if not token_file:
            try:
                token_file = settings.GOOGLE_OAUTH2_TOKEN_JSON
            except AttributeError:
                # If setting is not available, use default path
                token_file = Path(__file__).resolve().parent.parent.parent.parent / "gmail_tokens.json"
                self.stdout.write(f"Using default token path: {token_file}")
        
        # Check if client secrets file exists
        if not os.path.exists(client_secrets_file):
            self.stdout.write(self.style.ERROR(f"Client secrets file not found: {client_secrets_file}"))
            self.stdout.write("Please create a google_oauth_client.json file with your OAuth credentials")
            return
        
        # Define scopes - IMPORTANT: Include all required scopes
        scopes = [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.readonly",  # Add this for profile access
            "https://www.googleapis.com/auth/userinfo.email",
            "openid"
        ]
        self.stdout.write(f"Using scopes: {scopes}")
        
        # Create the flow using client secrets file
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secrets_file,
            scopes=scopes,
            redirect_uri=f'http://localhost:{port}/'
        )
        
        # Add these parameters to force consent and get a refresh token
        flow.oauth2session.params = {
            'access_type': 'offline',
            'prompt': 'consent',
            'include_granted_scopes': 'true'
        }
        
        # Run the OAuth flow
        self.stdout.write(self.style.SUCCESS(f"Opening browser for OAuth consent..."))
        self.stdout.write(self.style.SUCCESS(f"Using redirect URI: http://localhost:{port}/"))
        self.stdout.write(self.style.WARNING("Make sure this URI is authorized in your Google Cloud Console!"))
        
        try:
            # Force approval prompt to get refresh token
            credentials = flow.run_local_server(
                port=port,
                authorization_prompt_message="Please visit this URL to authorize access: {url}",
                success_message="Authentication successful! You can close this window.",
                open_browser=True
            )
            
            self.stdout.write(self.style.SUCCESS("OAuth flow completed successfully"))
            self.stdout.write(f"Access token: {credentials.token[:10]}...")
            self.stdout.write(f"Refresh token: {credentials.refresh_token[:10] if credentials.refresh_token else 'None'}...")
            
            if not credentials.refresh_token:
                self.stdout.write(self.style.ERROR("No refresh token received! You need to revoke access and try again."))
                self.stdout.write("1. Go to https://myaccount.google.com/permissions")
                self.stdout.write("2. Revoke access for your application")
                self.stdout.write("3. Run this command again")
                return
            
            # Save the credentials to the token file
            token_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            with open(token_file, 'w') as f:
                json.dump(token_data, f)
                
            self.stdout.write(self.style.SUCCESS(f"Gmail API credentials saved to {token_file}"))
            
            # Test the credentials
            try:
                service = build('gmail', 'v1', credentials=credentials)
                profile = service.users().getProfile(userId='me').execute()
                self.stdout.write(self.style.SUCCESS(f"Successfully authenticated as: {profile.get('emailAddress')}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error testing credentials: {str(e)}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"OAuth flow failed: {str(e)}"))
            self.stdout.write(self.style.WARNING("You need to update your Google Cloud Console settings:"))
            self.stdout.write("1. Go to https://console.cloud.google.com/apis/credentials")
            self.stdout.write("2. Find your OAuth 2.0 Client ID")
            self.stdout.write("3. Add this redirect URI: http://localhost:8080/")
            self.stdout.write("4. Save changes and try again")
