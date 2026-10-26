from django.db import models
from .managers import TicketArchiveManager
from simple_history.models import HistoricalRecords

# Create your models here.

class Ticket(models.Model):

    """
    A support request opened by a user.

    Attributes:
        STATUS_CHOICE: Available statuses: ``open`` (new), ``progress`` (under
            review), ``reply`` (staff have replied and the user is expected to
            answer) and ``closed``.
        DEPARTMENT_CHOICE: Departments a ticket can be sent to: ``finance``,
            ``technical`` and ``account``.
        profile: The user who opened the ticket; deleting the profile deletes
            the ticket.
        subject: Short subject line (up to 24 characters).
        department: The department that should handle the ticket.
        content: Description of the problem.
        status: Current status, ``open`` by default.
        is_archived: Whether the ticket is archived. Set automatically when the
            ticket is closed.
        created_date: When the ticket was opened.
        updated_date: When the ticket was last saved.

    Note:
        ``Ticket.objects`` is ``TicketArchiveManager`` and hides archived
        tickets; use ``Ticket._base_manager`` to include them. Deleting a ticket
        only archives it. The status is changed automatically by the signals in
        ``tickets.signals`` whenever a message is added.
    """

    STATUS_CHOICE = (
        ('open', 'باز'),
        ('progress', 'درحال بررسی'),
        ('reply', 'در انتظار پاسخ'),
        ('closed', 'بسته شده'),
    )

    DEPARTMENT_CHOICE = (
        ('finance', 'مالی'),
        ('technical', 'فنی'),
        ('account', 'اکانت')
    )

    profile = models.ForeignKey(
        'accounts.Profile',
        verbose_name = 'کاربر',
        on_delete = models.CASCADE,
        related_name = 'ticket',
    )

    subject = models.CharField(verbose_name = 'موضوع', max_length = 24)
    department = models.CharField(
        verbose_name = 'تیم فنی',
        choices = DEPARTMENT_CHOICE,
        max_length = 10
    )
    content = models.TextField(verbose_name = 'شرح مشکل', max_length = 255)
    status = models.CharField(
        verbose_name = 'وضعیت',
        choices = STATUS_CHOICE,
        default = 'open',
        max_length = 10
    )

    is_archived = models.BooleanField(
        verbose_name = 'بایگانی شده',
        default = False
    )

    objects = TicketArchiveManager()

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'تیکت'
        verbose_name_plural = 'تیکتها'
        ordering = ('created_date',)

    def __str__(self):
        return f'{self.profile.user} - {self.department} - {self.subject} - {self.status}'

    def save(self,*args, **kwargs):

        """
        Save the ticket, archiving it if it is closed.

        Sets ``is_archived`` to ``True`` whenever the status is ``closed``.

        Args:
            *args: Passed to ``Model.save``.
            **kwargs: Passed to ``Model.save``.

        Note:
            Reopening a ticket does not clear ``is_archived`` automatically; set it
            back to ``False`` yourself, as the admin's reopen action does.
        """

        if self.status == 'closed':
            self.is_archived = True
        
        super().save(*args, **kwargs)

    def delete(self, using = None, keep_parents = False):

        """
        Soft-delete the ticket: close and archive it instead of removing it.

        The row and its messages are kept.

        Args:
            using: Accepted for compatibility with ``Model.delete``; ignored.
            keep_parents: Accepted for compatibility with ``Model.delete``; ignored.

        Returns:
            ``None`` (unlike ``Model.delete``, which returns a count).

        Note:
            This is recorded in history as a change, not as a deletion. Bulk
            deletion through a queryset (``queryset.delete()``) does not call this
            method and removes the rows for good.
        """
        
        self.is_archived = True
        self.status = 'closed'
        self.save()


class Message(models.Model):

    """
    One message in a ticket conversation.

    Attributes:
        ticket: The ticket the message belongs to (reverse name ``message``);
            deleting the ticket deletes its messages.
        sender: The profile that wrote the message, either the ticket owner or
            a staff member. The automatic reply is sent by the ``system``
            profile.
        message: The message text.
        created_date: When the message was written.
        updated_date: When the message was last saved.

    Note:
        Saving a message updates the ticket's status: ``reply`` if the sender is
        staff, otherwise ``progress``.
    """

    ticket = models.ForeignKey(
        Ticket,
        on_delete = models.CASCADE,
        related_name = 'message'
    )
    sender = models.ForeignKey(
        'accounts.Profile',
        verbose_name = 'کاربر',
        on_delete = models.CASCADE,
        related_name = 'message'
    )
    message = models.TextField(verbose_name = 'متن پیام',)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'پیام'
        verbose_name_plural = 'پیامها'
        ordering = ('created_date',)

    def __str__(self):
        return f'{self.sender} - {self.ticket}'
