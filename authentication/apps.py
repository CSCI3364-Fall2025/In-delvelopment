from django.apps import AppConfig
from django.db.models.signals import post_migrate

class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'

    def ready(self):
        # Import signal handlers
        import authentication.signals
        
        # Register the post_migrate signal to set up OAuth
        # Only connect the signal once to avoid duplicate registrations
        post_migrate.connect(self.setup_oauth, sender=self, dispatch_uid="setup_oauth_once")
        
        # Register a signal to fix invalid JSON data
        post_migrate.connect(self.fix_invalid_json, sender=self, dispatch_uid="fix_invalid_json_once")
        
        # Move the admin customization here to avoid early imports
        self.customize_admin()
    
    def customize_admin(self):
        """Customize the admin interface for SocialApp"""
        try:
            from django.contrib import admin
            from allauth.socialaccount.models import SocialApp
            from allauth.socialaccount.admin import SocialAppAdmin
            
            # Only unregister if it's already registered
            if SocialApp in admin.site._registry:
                admin.site.unregister(SocialApp)
                
                # Create a custom admin class if needed
                class CustomSocialAppAdmin(SocialAppAdmin):
                    pass
                
                admin.site.register(SocialApp, CustomSocialAppAdmin)
        except Exception as e:
            # This might happen if the admin site isn't ready yet
            print(f"Could not customize admin: {e}")
    
    def fix_invalid_json(self, **kwargs):
        """Fix any invalid JSON in the progress_data field"""
        # Avoid running during app checks or other non-migration operations
        if kwargs.get('plan') is None:
            return
            
        try:
            # Import here to avoid circular imports
            from authentication.models import UserProfile
            import json
            
            # Get all profiles
            profiles = UserProfile.objects.all()
            fixed_count = 0
            
            for profile in profiles:
                if profile.progress_data is not None:
                    try:
                        # Test if it's valid JSON by parsing it
                        json.loads(profile.progress_data)
                    except (json.JSONDecodeError, TypeError):
                        # If not valid JSON, set to empty JSON object or null
                        profile.progress_data = '{}'  # or None if you prefer
                        profile.save()
                        fixed_count += 1
            
            if fixed_count > 0:
                print(f"Fixed {fixed_count} UserProfile records with invalid JSON data")
                
        except Exception as e:
            print(f"Could not fix invalid JSON data: {e}")
    
    def setup_oauth(self, **kwargs):
        """Set up OAuth configuration automatically"""
        # Avoid running during app checks or other non-migration operations
        if kwargs.get('plan') is None:
            return
            
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
