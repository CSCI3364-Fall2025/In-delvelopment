from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialAccount, SocialToken
from django.contrib.auth import get_user_model
from django.utils import timezone

class Command(BaseCommand):
    help = 'Check Gmail API tokens for users'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email of specific user to check')
        parser.add_argument('--fix', action='store_true', help='Attempt to fix issues by clearing invalid tokens')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options.get('email')
        fix_issues = options.get('fix', False)
        
        # Filter users
        if email:
            users = User.objects.filter(email=email)
            self.stdout.write(f"Checking Gmail tokens for user: {email}")
        else:
            users = User.objects.filter(profile__role='professor')
            self.stdout.write(f"Checking Gmail tokens for all professors")
        
        if not users.exists():
            self.stdout.write(self.style.ERROR("No matching users found"))
            return
            
        self.stdout.write(f"Found {users.count()} users to check")
        
        for user in users:
            self.stdout.write(f"\nChecking user: {user.email}")
            
            # Check if user has a Google account
            try:
                social_account = SocialAccount.objects.get(user=user, provider='google')
                self.stdout.write(f"  ✓ Has Google account: {social_account.uid}")
                
                # Check if user has a token
                try:
                    token = SocialToken.objects.get(account=social_account)
                    self.stdout.write(f"  ✓ Has access token: {token.token[:10]}...")
                    
                    # Check if token has expired
                    if token.expires_at and token.expires_at < timezone.now():
                        self.stdout.write(self.style.WARNING(f"  ✗ Token expired on: {token.expires_at}"))
                        if fix_issues:
                            if token.token_secret:
                                self.stdout.write("    Has refresh token, will be refreshed automatically")
                            else:
                                token.delete()
                                self.stdout.write(self.style.SUCCESS("    Deleted expired token without refresh token"))
                    else:
                        self.stdout.write(f"  ✓ Token valid until: {token.expires_at}")
                    
                    # Check if token has refresh token
                    if token.token_secret:
                        self.stdout.write(f"  ✓ Has refresh token: {token.token_secret[:5]}...")
                    else:
                        self.stdout.write(self.style.ERROR("  ✗ No refresh token found"))
                        if fix_issues:
                            token.delete()
                            self.stdout.write(self.style.SUCCESS("    Deleted token without refresh token"))
                
                except SocialToken.DoesNotExist:
                    self.stdout.write(self.style.ERROR("  ✗ No token found"))
            
            except SocialAccount.DoesNotExist:
                self.stdout.write(self.style.ERROR("  ✗ No Google account connected"))
        
        self.stdout.write("\nRecommendations:")
        self.stdout.write("1. Users without tokens or with expired tokens need to re-authenticate")
        self.stdout.write("2. To get a refresh token, users must:")
        self.stdout.write("   - Revoke access at https://myaccount.google.com/permissions")
        self.stdout.write("   - Log out and log in again with Google")
