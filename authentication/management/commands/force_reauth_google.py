from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Force a user to re-authenticate with Google and get a new token'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email of user to re-authenticate')

    def handle(self, *args, **options):
        email = options.get('email')
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No user found with email: {email}"))
            return
            
        self.stdout.write(f"Processing user: {user.email}")
        
        # Check if user has a Google account
        try:
            social_account = SocialAccount.objects.get(user=user, provider='google')
            self.stdout.write(f"Found Google account: {social_account.uid}")
            
            # Delete any existing tokens
            tokens = SocialToken.objects.filter(account=social_account)
            if tokens.exists():
                tokens.delete()
                self.stdout.write("Deleted existing tokens")
            else:
                self.stdout.write("No existing tokens found")
                
            # Print instructions for the user
            self.stdout.write(self.style.SUCCESS("\nInstructions for user:"))
            self.stdout.write("1. Go to https://myaccount.google.com/permissions")
            self.stdout.write("2. Find 'Peer Assessment System' and click 'Remove Access'")
            self.stdout.write("3. Log out of the application")
            self.stdout.write("4. Log back in with Google")
            self.stdout.write("5. Make sure to click 'Allow' on all permission screens")
            
        except SocialAccount.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No Google account found for user: {email}"))
