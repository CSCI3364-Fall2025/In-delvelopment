from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Fix OAuth configuration for Google'

    def add_arguments(self, parser):
        parser.add_argument('--client_id', type=str, help='Google OAuth client ID')
        parser.add_argument('--client_secret', type=str, help='Google OAuth client secret')

    def handle(self, *args, **options):
        # Get client ID and secret from arguments or use defaults
        client_id = options.get('client_id') or "583548039994-u848qtlu661loq7759f7r6q9m1j8269a.apps.googleusercontent.com"
        client_secret = options.get('client_secret') or "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"
        
        # Set up the site
        site, created = Site.objects.get_or_create(
            id=1,
            defaults={'domain': '127.0.0.1:8000', 'name': 'Local Development'}
        )
        
        if not created:
            site.domain = '127.0.0.1:8000'
            site.name = 'Local Development'
            site.save()
            self.stdout.write(f"Updated site: {site.domain}")
        else:
            self.stdout.write(f"Created site: {site.domain}")
        
        # Set up the Google OAuth app
        social_app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': client_secret,
            }
        )
        
        if not created:
            social_app.client_id = client_id
            social_app.secret = client_secret
            social_app.save()
            self.stdout.write(f"Updated Google OAuth app with client ID: {client_id[:10]}...")
        else:
            self.stdout.write(f"Created Google OAuth app with client ID: {client_id[:10]}...")
        
        # Connect the app to the site
        social_app.sites.add(site)
        
        # Check for accounts without tokens
        accounts_without_tokens = []
        for account in SocialAccount.objects.filter(provider='google'):
            if not SocialToken.objects.filter(account=account).exists():
                accounts_without_tokens.append(account.user.email)
        
        if accounts_without_tokens:
            self.stdout.write(self.style.WARNING(
                f"Found {len(accounts_without_tokens)} accounts without tokens: {', '.join(accounts_without_tokens)}"
            ))
            self.stdout.write("Run 'python manage.py fix_oauth_tokens' to create placeholder tokens")
        
        self.stdout.write(self.style.SUCCESS("Successfully fixed OAuth configuration"))
