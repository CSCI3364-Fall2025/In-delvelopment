from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'

    def ready(self):
        # Import signal handlers
        import authentication.signals
        
        # Register the post_migrate signal to set up OAuth
        post_migrate.connect(self.setup_oauth, sender=self)
    
    def setup_oauth(self, **kwargs):
        """Set up OAuth configuration automatically"""
        # Use a hardcoded client ID and secret for development
        # In production, these would come from environment variables
        GOOGLE_CLIENT_ID = "583548039994-u848qtlu661loq7759f7r6q9m1j8269a.apps.googleusercontent.com"
        GOOGLE_CLIENT_SECRET = "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"
        
        # Avoid circular imports
        from django.contrib.sites.models import Site
        from allauth.socialaccount.models import SocialApp
        
        # Set up the site
        try:
            site, created = Site.objects.get_or_create(
                id=1,
                defaults={'domain': '127.0.0.1:8000', 'name': 'Local Development'}
            )
            if not created:
                site.domain = '127.0.0.1:8000'
                site.name = 'Local Development'
                site.save()
                
            # Set up the Google OAuth app
            social_app, created = SocialApp.objects.get_or_create(
                provider='google',
                defaults={
                    'name': 'Google',
                    'client_id': GOOGLE_CLIENT_ID,
                    'secret': GOOGLE_CLIENT_SECRET,
                }
            )
            
            if not created:
                social_app.client_id = GOOGLE_CLIENT_ID
                social_app.secret = GOOGLE_CLIENT_SECRET
                social_app.save()
                
            # Connect the app to the site
            social_app.sites.add(site)
            
            print("Successfully set up OAuth configuration")
        except Exception as e:
            # This might happen if the database tables don't exist yet
            print(f"Could not set up OAuth configuration: {e}")
