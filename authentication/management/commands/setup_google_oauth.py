from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

class Command(BaseCommand):
    help = 'Sets up Google OAuth credentials for Django Allauth'

    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up Google OAuth credentials...')
        
        # Google OAuth credentials
        client_id = '583548039994-u848qtlu661loq7759f7r6q9m1j8269a.apps.googleusercontent.com'
        secret_key = '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'
        
        # Get or create the default site
        site, created = Site.objects.get_or_create(
            id=1,
            defaults={
                'domain': 'localhost:8000',
                'name': 'localhost'
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created site: {site.domain}'))
        
        # Create or update the Google SocialApp
        social_app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name': 'Google OAuth',
                'client_id': client_id,
                'secret': secret_key,
                'key': ''  # Google doesn't require a key
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created Google OAuth application'))
        else:
            self.stdout.write(self.style.SUCCESS('Updated Google OAuth application'))
        
        # Make sure the site is associated with the app
        social_app.sites.add(site)
        
        self.stdout.write(self.style.SUCCESS('Google OAuth setup complete!'))
