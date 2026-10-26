from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Message, Ticket
from accounts.models import Profile

"""
Signals for the tickets app.

Sends an automatic reply for every new ticket and keeps a ticket's status in
sync with the messages written in it.
"""

User = get_user_model()

def get_system_profile():

    """
    Return the profile of the internal ``system`` user, creating it if needed.

    The ``system`` user is the sender of automatic replies. It is created on first
    use, as an inactive account that cannot log in.

    Returns:
        The ``Profile`` of the ``system`` user.

    Note:
        The user and profile are hidden from the admin user and profile lists and
        from the dashboard statistics.
    """

    user, _ = User.objects.get_or_create(
        username = 'system',
        defaults = {
            'email': 'system@support.local',
            'is_active': False,
            'is_verified': True,
        }
    )

    profile, _ = Profile.objects.get_or_create(user=user)

    return profile

@receiver(post_save,sender=Ticket)
def ticket_system_response(sender,instance,created,**kwargs):

    """
    Send an automatic acknowledgement when a ticket is created.

    Adds a message from the ``system`` profile to every new ticket. Skipped for
    fixture loading (``raw``) and for tickets that are only updated.

    Args:
        sender: The ``Ticket`` model class.
        instance: The ticket that was saved.
        created: ``True`` if the ticket was just created.
        **kwargs: Extra signal arguments; ``raw`` is checked.

    Note:
        Saving this message triggers ``ticket_status_changer``, so a new ticket
        moves from ``open`` to ``progress`` immediately.
    """

    if kwargs.get('raw') or not created:
        return
    

    Message.objects.create(
        ticket = instance,
        sender = get_system_profile(),
        message = (
    f'Thanks for your ticket. Our {instance.department} support team '
    f'will review your request as soon as possible. '
    f'We appreciate your patience.'
        ),
    )

@receiver(post_save,sender=Message)
def ticket_status_changer(sender,instance,created,**kwargs):

    """
    Update a ticket's status whenever a message is saved.

    A message from a staff member sets the status to ``reply`` (waiting for the
    user); a message from anyone else, including the ``system`` profile, sets it
    to ``progress`` (waiting for staff).

    Args:
        sender: The ``Message`` model class.
        instance: The message that was saved.
        created: ``True`` if the message was just created.
        **kwargs: Extra signal arguments; ``raw`` is checked.
    """

    if kwargs.get('raw'):
        return
    
    ticket = instance.ticket

    if instance.sender.user.is_staff:
        ticket.status = 'reply'

    else:
        ticket.status = 'progress'

    ticket.is_archived = False
    ticket.save(update_fields=['status', 'is_archived', 'updated_date'])