from django.contrib.auth.models import BaseUserManager
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse

"""
``UserManager`` creates users and superusers identified by phone number.
``VerificationManager`` builds verification links and sends them through a
verification backend.
"""

class UserManager(BaseUserManager):

    """Manager for the custom user model, which logs in with a phone number."""

    def create_user(self,phone,password,**extra_fields):
        
        """
        Create and save a user with a phone number and a password.

        Args:
            phone: The phone number, used as the login identifier.
            password: The raw password; it is hashed before saving.
            **extra_fields: Any other fields of the user model.

        Returns:
            The saved user.

        Raises:
            ValueError: If ``phone`` is empty.

        Note:
            The password is required, so a user cannot be created with an unusable
            password.
        """

        if not phone:
            raise ValueError(_("The Phone Number Must Be Given."))
        user = self.model(phone=phone,**extra_fields)
        user.set_password(password)
        user.save()
        return user
    
    def create_superuser(self,phone,password,**extra_fields):


        """
        Create and save a superuser.

        ``is_staff``, ``is_active``, ``is_verified`` and ``is_superuser`` default to
        ``True``, so a superuser is verified from the start.

        Args:
            phone: The phone number, used as the login identifier.
            password: The raw password; it is hashed before saving.
            **extra_fields: Any other fields of the user model.

        Returns:
            The saved superuser.

        Raises:
            ValueError: If ``is_staff`` or ``is_superuser`` is explicitly set to
                anything other than ``True``.
        """

        extra_fields.setdefault("is_staff",True)
        extra_fields.setdefault("is_active",True)
        extra_fields.setdefault("is_verified",True)
        extra_fields.setdefault("is_superuser",True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Staff Must Be TRUE."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("SuperUser Must Be TRUE."))
        
        return self.create_user(phone,password,**extra_fields)
    

class VerificationManager:

    """
    Create verification links and send them through a chosen backend.

    Args:
        request: Optional current request. When given, its host is used in the
        generated links; otherwise the domain of the current ``Site`` is used.
    """

    def __init__(self,request=None):
        self.request = request

    def _generate_link(self, user, url_name):

        """
        Build an absolute verification link for a user.

        The link contains the user's base64-encoded id and a one-time token from
        Django's default token generator.

        Args:
            user: The user to verify.
            url_name: Name of the URL pattern that takes ``uidb64`` and ``token``.

        Returns:
            The full verification URL.
        """

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)


        if self.request:
            domain = self.request.get_host()
        else:
            current_site = Site.objects.get_current()
            domain = current_site.domain


        return f"http://{domain}{reverse(url_name, kwargs={'uidb64':uid, 'token':token})}"
    
    def trigger_verification(self, user, backend, url_name='accounts:Verify_email'):
        
        """
        Generate a verification link and send it to the user.

        Args:
            user: The user to verify.
            backend: A verification backend *class* (for example
                ``EmailVerificationBackend``), not an instance. It is instantiated
                here and its ``send`` method is called.
            url_name: Name of the URL pattern used to build the link.
        """

        link = self._generate_link(user, url_name)
        backend = backend()
        backend.send(user, link)