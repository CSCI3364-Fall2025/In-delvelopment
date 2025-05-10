from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test email sending with current backend'

    def add_arguments(self, parser):
        parser.add_argument('--to', type=str, help='Email recipient')

    def handle(self, *args, **options):
        recipient = options.get('to') or 'your-test-email@example.com'
        
        self.stdout.write(f"Current email backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"USE_GMAIL_API setting: {settings.USE_GMAIL_API}")
        
        try:
            self.stdout.write(f"Sending test email to {recipient}...")
            
            result = send_mail(
                subject='Test Email from Django',
                message='This is a test email sent from your Django application.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            
            if result:
                self.stdout.write(self.style.SUCCESS(f"Email sent successfully!"))
            else:
                self.stdout.write(self.style.ERROR(f"Email sending failed."))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error sending email: {str(e)}"))
