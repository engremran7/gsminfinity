"""
CSP Nonce Middleware
Generates a unique nonce for each request and makes it available in templates.
The nonce is used by SecurityHeadersMiddleware to build the CSP header.

This middleware ONLY generates the nonce. SecurityHeadersMiddleware handles CSP headers.
"""
import secrets

from django.utils.deprecation import MiddlewareMixin


class CSPNonceMiddleware(MiddlewareMixin):
    """
    Middleware to generate CSP nonces for requests.
    The nonce is available in templates as {{ request.csp_nonce }}
    
    Note: This middleware ONLY generates the nonce and attaches it to the request.
    The SecurityHeadersMiddleware is responsible for including the nonce in CSP headers.
    """

    def process_request(self, request):
        """Generate a unique nonce for this request"""
        # Generate cryptographically secure random nonce
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce

    # No process_response needed - SecurityHeadersMiddleware handles CSP headers
