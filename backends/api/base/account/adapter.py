from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter for ResSynt platform.
    Disables public registration and customizes email settings.
    """
    
    def is_open_for_signup(self, request):
        """Disable public registration - users must be created by admin."""
        return False
    
    def get_from_email(self):
        """Return the display name with email address."""
        return 'ResSynt - Research Data Management Platform'
    
    def get_login_redirect_url(self, request):
        """Redirect based on user role after login."""
        if request.user.is_superuser:
            return '/admin/'
        return '/select-study/'