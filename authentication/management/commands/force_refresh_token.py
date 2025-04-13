from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp
from django.contrib.auth import get_user_model
import requests
import json
import time

class Command(BaseCommand):
    help = 'Force refresh token acquisition for a user'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email of user')
        parser.add_argument('--revoke', action='store_true', help='Revoke existing tokens via Google API')

    def handle(self, *args, **options):
        email = options.get('email')
        revoke = options.get('revoke', False)
        
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No user found with email: {email}"))
            return
            
        # Check if user has a Google account
        try:
            social_account = SocialAccount.objects.get(user=user, provider='google')
            self.stdout.write(f"Found Google account: {social_account.uid}")
            
            # Check if user has tokens
            try:
                token = SocialToken.objects.get(account=social_account)
                self.stdout.write(f"Found token: {token.token[:10]}...")
                
                if token.token_secret:
                    self.stdout.write(f"Has refresh token: {token.token_secret[:5]}...")
                else:
                    self.stdout.write(self.style.WARNING("No refresh token found"))
                
                # Revoke the token if requested
                if revoke:
                    self.stdout.write("Revoking token via Google API...")
                    
                    # Try to revoke access token
                    revoke_url = f"https://accounts.google.com/o/oauth2/revoke?token={token.token}"
                    try:
                        response = requests.get(revoke_url)
                        if response.status_code == 200:
                            self.stdout.write(self.style.SUCCESS("✓ Token revoked successfully via Google API"))
                        else:
                            self.stdout.write(self.style.WARNING(f"✗ Failed to revoke token: {response.status_code}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"✗ Error revoking token: {str(e)}"))
                    
                    # Delete the token from our database
                    token.delete()
                    self.stdout.write(self.style.SUCCESS("✓ Token deleted from database"))
                
            except SocialToken.DoesNotExist:
                self.stdout.write("No token found in database")
            
            # Print instructions
            self.stdout.write("\nTo get a new refresh token, the user must:")
            self.stdout.write("1. Go to https://myaccount.google.com/permissions")
            self.stdout.write("2. Find your app and click 'Remove Access'")
            self.stdout.write("3. Log out of your application")
            self.stdout.write("4. Log back in with Google")
            self.stdout.write("5. Make sure to accept all permissions")
            
            # Generate login URL
            try:
                social_app = SocialApp.objects.get(provider='google')
                self.stdout.write("\nDirect login URL (for testing):")
                self.stdout.write(f"http://localhost:8000/accounts/google/login/?process=login&next=/reauth-google/")
            except SocialApp.DoesNotExist:
                pass
                
        except SocialAccount.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No Google account found for user: {email}"))
