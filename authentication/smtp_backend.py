# authentication/smtp_backend.py
from django.core.mail.backends.smtp import EmailBackend
import logging
import ssl

logger = logging.getLogger(__name__)

class GoogleSMTPBackend(EmailBackend):
    """
    A Django email backend that uses Google SMTP with app password.
    """
    
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None,
                 **kwargs):
        
        # Default Google SMTP settings
        host = host or 'smtp.gmail.com'
        port = port or 587
        use_tls = True if use_tls is None else use_tls
        
        logger.debug(f"Initializing Google SMTP backend with username: {username}")
        
        # Create a custom SSL context that doesn't verify certificates
        # This is a workaround for certificate verification issues
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        super().__init__(
            host=host, port=port, username=username, password=password,
            use_tls=use_tls, fail_silently=fail_silently, use_ssl=use_ssl,
            timeout=timeout, ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile,
            **kwargs
        )
    
    def open(self):
        """
        Ensures the connection is open and ready for use.
        Overrides the parent method to use our custom SSL context.
        """
        if self.connection:
            return False
            
        connection_params = {}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        if self.use_ssl:
            connection_params['context'] = self.ssl_context
            
        try:
            self.connection = self.connection_class(self.host, self.port, **connection_params)
            
            # TLS/SSL are mutually exclusive, so only use one
            if self.use_tls:
                self.connection.starttls(context=self.ssl_context)
            
            if self.username and self.password:
                self.connection.login(self.username, self.password)
                
            return True
        except Exception as e:
            logger.error(f"Error connecting to SMTP server: {str(e)}")
            if not self.fail_silently:
                raise
            return False