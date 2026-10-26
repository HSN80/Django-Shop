from django.contrib import admin
from django.db.models import Count
from simple_history.admin import SimpleHistoryAdmin
from .models import Ticket, Message

# Register your models here.

"""
Admin configuration for the tickets app.

Lets staff read tickets, reply from the ticket page and close or reopen
tickets in bulk. Archived (closed) tickets stay visible, and bulk deletion is
disabled because it would remove records permanently.
"""

class MessageInline(admin.TabularInline):

    """
    Inline list of a ticket's messages: existing ones are read-only and an
    empty row is shown for a new reply.
    """

    model = Message
    extra = 1
    fields = ('sender', 'message', 'created_date')
    readonly_fields = ('created_date',)
    raw_id_fields = ('sender',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        """
        Pre-fill the sender of a new reply with the current staff member's profile.

        Args:
            db_field: The foreign-key field being rendered.
            request: The current admin request.
            **kwargs: Passed on to the parent method.

        Returns:
            The form field for ``db_field``.

        Note:
            If the staff member has no profile, the sender must be chosen by hand.
            The ticket moves to ``reply`` status only when the sender is a staff
            user (see ``ticket_status_changer``).
        """

        if db_field.name == 'sender' and hasattr(request.user, 'profile'):
            kwargs['initial'] = request.user.profile.pk
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Ticket)
class TicketAdmin(SimpleHistoryAdmin):

    """
    Admin for ``Ticket`` with change history, filters, search and bulk actions.

    Messages appear inline on the ticket page. The list includes archived tickets
    and shows a message count per ticket.
    
    Note:
        The "delete selected" action is removed: a bulk delete bypasses the
        ticket's soft delete and would erase the tickets and their messages for
        good. Use the close action instead.
    """

    list_display = (
        'id', 'subject', 'profile', 'department', 'status',
        'is_archived', 'messages_count', 'updated_date',
    )
    list_filter = ('status', 'department', 'is_archived', 'created_date')
    search_fields = ('subject', 'content', 'profile__user__username', 'profile__user__phone')
    list_select_related = ('profile__user',)
    raw_id_fields = ('profile',)
    ordering = ('-updated_date',)
    inlines = [MessageInline]
    actions = ['close_tickets', 'reopen_tickets']

    def get_queryset(self, request):

        """
        Return all tickets, including archived ones, with a message count.
        
        The default manager hides archived tickets, so the base manager is used
        instead. Adds the ``messages_count`` annotation.
        """

        return self.model._base_manager.annotate(messages_count=Count('message'))

    def get_actions(self, request):

        """Return the available bulk actions without "delete selected"."""

        actions = super().get_actions(request)
        # حذف دسته‌ای به‌جای بایگانی، رکورد را واقعاً پاک می‌کند
        actions.pop('delete_selected', None)
        return actions

    @admin.display(description='پیام‌ها', ordering='messages_count')
    def messages_count(self, obj):

        """Show the number of messages, taken from the ``messages_count`` annotation."""

        return obj.messages_count

    @admin.action(description='بستن تیکت‌های انتخاب‌شده')
    def close_tickets(self, request, queryset):

        """
        Close the selected tickets.

        Each ticket is saved with the ``closed`` status and a change reason, so the
        change is recorded in history.

        Note:
            Saving a closed ticket also archives it (``Ticket.save``).
        """

        for ticket in queryset:
            ticket.status = 'closed'
            ticket._change_reason = 'بسته شد (action ادمین)'
            ticket.save()

    @admin.action(description='بازکردن دوباره تیکت‌های انتخاب‌شده')
    def reopen_tickets(self, request, queryset):

        """
        Reopen the selected tickets.

        Sets the status back to ``open`` and clears ``is_archived``. Each ticket is
        saved with a change reason, so the change is recorded in history.
        """

        for ticket in queryset:
            ticket.status = 'open'
            ticket.is_archived = False
            ticket._change_reason = 'دوباره باز شد (action ادمین)'
            ticket.save()


@admin.register(Message)
class MessageAdmin(SimpleHistoryAdmin):

    """
    Read-only admin for ``Message``.

    Messages cannot be added or edited here; replies are written from the ticket
    page. The list shows the ticket and sender and supports searching by message
    text or sender username.
    """

    list_display = ('id', 'ticket', 'sender', 'created_date')
    list_select_related = ('ticket__profile__user', 'sender__user')
    search_fields = ('message', 'sender__user__username')

    def has_add_permission(self, request):

        """Disallow adding messages from this list; reply from the ticket page."""
        
        return False

    def has_change_permission(self, request, obj=None):

        """Make messages read-only in this admin."""
        
        return False