from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.utils import timezone
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Reset OAuth tokens to force re-authentication'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email of specific user to reset')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options.get('email')
        
        # Filter accounts
        if email:
            accounts = SocialAccount.objects.filter(
                user__email=email, 
                provider='google'
            )
            self.stdout.write(f"Looking for Google account for user: {email}")
        else:
            accounts = SocialAccount.objects.filter(provider='google')
            self.stdout.write(f"Looking for all Google accounts")
        
        if not accounts.exists():
            self.stdout.write(self.style.ERROR("No matching Google accounts found"))
            return
            
        self.stdout.write(f"Found {accounts.count()} Google accounts")
        
        # Delete tokens for these accounts
        for account in accounts:
            tokens = SocialToken.objects.filter(account=account)
            if tokens.exists():
                count = tokens.count()
                tokens.delete()
                self.stdout.write(f"Deleted {count} tokens for {account.user.email}")
            else:
                self.stdout.write(f"No tokens found for {account.user.email}")
        
        self.stdout.write(self.style.SUCCESS(
            "Tokens have been reset. Users will need to log in again to get new tokens."
        ))
        self.stdout.write(
            "IMPORTANT: Users must revoke access at https://myaccount.google.com/permissions "
            "before logging in again to ensure they get a refresh token."
        )