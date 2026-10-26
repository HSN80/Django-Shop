from django.db import models

"""Custom managers for the tickets app."""

class TicketArchiveManager(models.Manager):

    """
    Manager that hides archived tickets.

    Used as ``Ticket.objects``, so everyday queries (lists, dashboards, counts)
    return only tickets with ``is_archived=False``.

    Note:
        Because it is the default manager, Django also uses it where it falls
        back to the default manager, for example in admin querysets and in the
        choices of form fields that point at a ticket. Code that needs archived
        tickets as well must go through ``Ticket._base_manager``, as
        ``TicketAdmin`` and the user dossier do.
    """

    def get_queryset(self):
        
        """Return the base queryset limited to tickets that are not archived."""
        
        return super().get_queryset().filter(is_archived=False)
    
