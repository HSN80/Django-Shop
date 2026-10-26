from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

@receiver(post_save,sender=User)
def Save_Profile(sender,instance,created,**kwargs):

    """
    Create an empty ``Profile`` when a new user is created.

    Skipped for fixture loading (``raw``) and for users that are only updated.

    Args:
        sender: The ``User`` model class.
        instance: The user that was saved.
        created: ``True`` if the user was just created.
        **kwargs: Extra signal arguments; ``raw`` is checked.

    Note:
        The profile starts with blank fields; the user fills them in later.
    """

    if kwargs.get('raw'):
        return
    
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save,sender=User)
def SendEmailVerification(sender,instance,created,**kwargs):

    """
    Email a verification link to a newly created, unverified user.

    Superusers created with ``createsuperuser`` are already verified, so they do
    not receive an email.

    Args:
        sender: The ``User`` model class.
        instance: The user that was saved.
        created: ``True`` if the user was just created.
        **kwargs: Extra signal arguments; ``raw`` is checked.

    Note:
        ``VerificationManager`` and the backend are
        imported inside the function to avoid circular imports.
    """

    if kwargs.get('raw'):
        return 
    
    if created and not instance.is_verified:
        from .mangers import VerificationManager
        from .backends import EmailVerificationBackend

        manager = VerificationManager()
        manager.trigger_verification(instance, EmailVerificationBackend)