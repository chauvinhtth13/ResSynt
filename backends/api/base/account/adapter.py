from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False
    
    def get_from_email(self):
        """
        Return the display name with email address.
        """
        return 'ResSync- Research Data Management Platform'