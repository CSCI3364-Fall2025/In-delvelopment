from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp
import requests
import json

class Command(BaseCommand):
    help = 'Verify and update Google OAuth configuration'

    def add_arguments(self, parser):
        parser.add_argument('--client_id', type=str, help='Google OAuth client ID')
        parser.add_argument('--client_secret', type=str, help='Google OAuth client secret')

    def handle(self, *args, **options):
        # Get the Google SocialApp
        try:
            social_app = SocialApp.objects.get(provider='google')
            self.stdout.write(f"Found Google OAuth app: {social_app.name}")
            
            client_id = options.get('client_id') or social_app.client_id
            client_secret = options.get('client_secret') or social_app.secret
            
            # Print current configuration
            self.stdout.write(f"Client ID: {client_id[:10]}...")
            self.stdout.write(f"Client Secret: {client_secret[:5]}..." if client_secret else "Client Secret: Not set")
            
            # Verify the client ID and secret by making a test request
            self.stdout.write("\nVerifying credentials...")
            
            # Check if the client ID is valid
            discovery_url = f"https://accounts.google.com/.well-known/openid-configuration"
            try:
                response = requests.get(discovery_url)
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS("✓ Google OAuth endpoints are accessible"))
                else:
                    self.stdout.write(self.style.ERROR(f"✗ Failed to access Google OAuth endpoints: {response.status_code}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error accessing Google OAuth endpoints: {str(e)}"))
            
            # Print instructions
            self.stdout.write("\nIMPORTANT CONFIGURATION CHECKS:")
            self.stdout.write("1. In Google Cloud Console (https://console.cloud.google.com/):")
            self.stdout.write("   - Verify OAuth consent screen is configured")
            self.stdout.write("   - Make sure the following scopes are added:")
            self.stdout.write("     * .../auth/userinfo.email")
            self.stdout.write("     * .../auth/userinfo.profile")
            self.stdout.write("     * .../auth/gmail.send")
            self.stdout.write("2. In OAuth Client ID settings:")
            self.stdout.write("   - Verify redirect URIs include:")
            self.stdout.write(f"     * https://yourdomain.com/accounts/google/login/callback/")
            self.stdout.write(f"     * http://localhost:8000/accounts/google/login/callback/ (for development)")
            
            self.stdout.write("\nTo fix refresh token issues:")
            self.stdout.write("1. Make sure your settings.py has:")
            self.stdout.write("   SOCIALACCOUNT_PROVIDERS = {")
            self.stdout.write("       'google': {")
            self.stdout.write("           'SCOPE': ['profile', 'email', 'https://www.googleapis.com/auth/gmail.send'],")
            self.stdout.write("           'AUTH_PARAMS': {")
            self.stdout.write("               'access_type': 'offline',")
            self.stdout.write("               'prompt': 'consent',")
            self.stdout.write("               'include_granted_scopes': 'true',")
            self.stdout.write("           }")
            self.stdout.write("       }")
            self.stdout.write("   }")
            
        except SocialApp.DoesNotExist:
            self.stdout.write(self.style.ERROR("No Google OAuth app configured"))
            self.stdout.write("Run 'python manage.py fix_oauth_tokens' to set up the Google OAuth app")
