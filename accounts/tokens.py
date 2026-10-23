from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for doctor email confirmation.

    Reuses Django's built-in HMAC token infrastructure so we get
    expiry (default 3 days via PASSWORD_RESET_TIMEOUT) for free.
    """

    def _make_hash_value(self, user, timestamp):
        # Including is_active makes the token single-use: once the
        # email is confirmed (is_active becomes True) the token is invalid.
        return f"{user.pk}{timestamp}{user.is_active}{user.email}"


email_confirmation_token = EmailConfirmationTokenGenerator()
