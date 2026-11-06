from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Authenticate with either an email address or a username.

    Django calls `authenticate(request, username=..., password=...)` on every backend in
    AUTHENTICATION_BACKENDS until one returns a user. The React login form sends one
    "username" value, so we look it up against both columns.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        try:
            user = User.objects.get(Q(email__iexact=username) | Q(username=username))
        except User.DoesNotExist:
            # Hash anyway so "unknown user" and "wrong password" take similar time
            # (stops attackers discovering which accounts exist by measuring response time).
            User().set_password(password)
            return None
        # user_can_authenticate() rejects inactive users (is_active=False).
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
