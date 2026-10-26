from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings


"""
Authentication and verification backends for the accounts app.

``MultiUsernameFieldBackend`` lets users log in with a username, email or
phone number. The ``*VerificationBackend`` classes deliver verification links
to users through different channels.
"""

User = get_user_model()


class MultiUsernameFieldBackend(ModelBackend):
    
    """Authentication backend that accepts a username, email or phone number.

        Extends ``ModelBackend``, so permission checks and the ``is_active`` rule
        (banned users cannot log in) work as usual.
    """

    def authenticate(self, request, username = None, password = None, **kwargs):

        """
        Authenticate a user by username, email or phone and a password.

        The identifier is matched case-insensitively against all three fields.

        Args:
            request: The current request.
            username: Login identifier: a username, an email or a phone number.
            password: The raw password to check.

        Returns:
            The matching user, or ``None`` if no user matches, the password is wrong
            or the account is inactive.
        """

        if username is None:
            return None

        try:
            user = User.objects.get(
                Q(username__iexact = username)|
                Q(email__iexact = username)|
                Q(phone__iexact = username)
            )
        except User.DoesNotExist:
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class BaseVerificationBackend:

    """
        Base class for channels that deliver a verification link to a user.
    """

    def send(self, user, link):

        """Deliver a verification link to the user.

        Args:
            user: The user to verify.
            link: The full verification URL.

        Raises:
            NotImplementedError: Always; subclasses must override this method.
        """

        raise NotImplementedError('send method must be implented in child class.')

class EmailVerificationBackend(BaseVerificationBackend):

    """
    Deliver verification links by email.
    """

    def send(self, user, link):

        """
        Email the verification link to the user.

        The greeting uses the profile's first name, or the username if it is empty.

        Args:
            user: The user to verify; ``user.email`` is the recipient.
            link: The full verification URL.
        """

        first_name = user.profile.first_name or user.username
        send_mail(
            subject='email verification',
            message=f'hi dear {first_name} ,\n to verify your email please click on link below \n{link}',
            recipient_list=[user.email],
            from_email=f'Django Shop Support <{settings.DEFAULT_FROM_EMAIL}>',
            fail_silently=False,
        )