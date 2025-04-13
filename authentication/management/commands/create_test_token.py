from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Create a test token for a user (for development only)'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True, help='Email of user')
        parser.add_argument('--token', type=str, required=True, help='Access token')
        parser.add_argument('--refresh', type=str, required=True, help='Refresh token')

    def handle(self, *args, **options):
        email = options.get('email')
        access_token = options.get('token')
        refresh_token = options.get('refresh')
        
        User = get_user_model()
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No user found with email: {email}"))
            return
            
        # Check if user has a Google account
        try:
            social_account = SocialAccount.objects.get(user=user, provider='google')
            
            # Delete any existing tokens
            SocialToken.objects.filter(account=social_account).delete()
            
            # Create a new token
            token = SocialToken.objects.create(
                account=social_account,
                token=access_token,
                token_secret=refresh_token,
                expires_at=timezone.now() + datetime.timedelta(hours=1)
            )
            
            self.stdout.write(self.style.SUCCESS(f"Created test token for {email}"))
            self.stdout.write(f"Token: {token.token[:10]}...")
            self.stdout.write(f"Refresh token: {token.token_secret[:5]}...")
            
        except SocialAccount.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No Google account found for user: {email}"))
