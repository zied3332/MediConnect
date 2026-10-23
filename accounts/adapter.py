from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model


class MediConnectSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom allauth adapter.

    - Assigns the 'patient' role to anyone who signs up via Google
      (doctors use the dedicated doctor signup flow instead).
    - Connects Google logins to existing accounts when email matches.
    - Redirects the user to their role dashboard after login.
    """

    def pre_social_login(self, request, sociallogin):
        """
        Called when a social account is about to be logged in.
        
        If a user with this email already exists (created via normal signup),
        connect the social account to that existing user instead of creating
        a duplicate account.
        """
        if sociallogin.is_existing:
            # Already connected, nothing to do
            return

        # Check if user with this email already exists
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return

        User = get_user_model()
        try:
            existing_user = User.objects.get(email__iexact=email)
            # Connect this social account to the existing user
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        """
        Called when creating a brand new user via social login.
        Assigns the 'patient' role by default.
        """
        user = super().save_user(request, sociallogin, form)
        # Only assign a role if the user is brand new and has no role yet
        if not user.role:
            User = get_user_model()
            user.role = User.Role.PATIENT
            user.save(update_fields=["role"])
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        """Where to redirect after connecting a social account."""
        return socialaccount.user.dashboard_url

    def get_login_redirect_url(self, request):
        """Where to redirect after social login."""
        user = request.user
        if user.is_authenticated:
            return user.dashboard_url
        return "/"
