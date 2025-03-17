from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class BCEmailMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Skip check for admin users and admin pages
            if request.user.is_staff or request.path.startswith('/admin/'):
                return self.get_response(request)
                
            # Check if email is from BC domain
            if not request.user.email.endswith('@bc.edu'):
                # Log the user out
                from django.contrib.auth import logout
                
                # Store the email before logging out
                email = request.user.email
                
                # Clear any success messages
                storage = messages.get_messages(request)
                for message in storage:
                    # Remove any success messages
                    if message.level == messages.SUCCESS:
                        storage.used = True
                
                # Perform logout
                logout(request)
                
                # Add error message
                messages.error(request, "Only Boston College (@bc.edu) email addresses are allowed.")
                
                # Redirect to custom error page with parameters
                return redirect(f'/login-error/?error=non_bc_email&email={email}')
        
        # Continue with the request
        return self.get_response(request) 