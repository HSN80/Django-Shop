from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    CreateView, DetailView, ListView, DeleteView
    )
from django.urls import reverse
from django.contrib import messages
from .models import Ticket, Message
from .froms import TicketCreateForm, MessageCreateForm

# Create your views here.

class TicketCreateView(LoginRequiredMixin,CreateView):

    """
    Open a new support ticket for the current user.

    Handles the POST of ``TicketCreateForm`` from the profile page. Requires
    login. The ticket is assigned to the current user's profile.

    Attributes:
        model: The ``Ticket`` model.
        form_class: The form that validates the subject, department and content.

    Note:
        The automatic acknowledgement reply and the initial status change are
        added by the signals in ``tickets.signals``.
    """

    model = Ticket
    form_class = TicketCreateForm
    # success_url = reverse_lazy('accounts:Profile')

    def form_valid(self, form):
        
        """Set the current user's profile as the ticket owner and save the ticket."""

        form.instance.profile = self.request.user.profile
        return super().form_valid(form)
    
    def form_invalid(self, form):
        
        """Report validation errors as messages and redirect back."""

        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request,f'{field}: {error}')

        return redirect(self.get_success_url())
    
    def get_success_url(self):
        
        """Return the profile page URL, pointing at the support tab."""

        return reverse('accounts:Profile') + '#account-tab-support'
    
class MessageCreateView(LoginRequiredMixin,CreateView):

    """
    Add a reply to one of the current user's own tickets.

    Handles the POST of ``MessageCreateForm``. Requires login, and the ticket
    (taken from ``ticket_id`` in the URL) must belong to the current user.
    
    Attributes:
        model: The ``Message`` model.
        form_class: The form that validates the message text.
    
    Note:
        Replies to closed tickets are refused with an error message. A saved
        reply sets the ticket's status to ``progress`` (see
        ``ticket_status_changer``).
    """

    model = Message
    form_class = MessageCreateForm

    def dispatch(self, request, *args, **kwargs):

        """
        Find the ticket being replied to before handling the request.

        Anonymous users are sent to the login page. Closed (archived) tickets are
        included in the lookup, so replying to one gives a clear error message
        instead of a 404.

        Raises:
            Http404: If the ticket does not exist or belongs to another user.
        """
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        self.ticket = get_object_or_404(
            Ticket._base_manager,
            id = self.kwargs['ticket_id'],
            profile = request.user.profile,
        )

        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):

        """
        Save the reply, unless the ticket is closed.

        For a closed ticket an error message is queued and nothing is saved. Otherwise
        the ticket and the current user's profile are set on the message.

        Returns:
            A redirect to the support tab of the profile page.
        """

        if self.ticket.status == 'closed':
            messages.error(self.request,'This ticket is closed.')
            return redirect(self.get_success_url())
        
        form.instance.ticket = self.ticket
        form.instance.sender = self.request.user.profile

        return super().form_valid(form)
    
    def form_invalid(self, form):

        """Report validation errors as messages and redirect back."""
        
        for error in form.errors.get('message', []):
            messages.error(self.request, error)

        return redirect(self.get_success_url())
    
    def get_success_url(self):

        """Return the profile page URL, pointing at the support tab."""

        return reverse('accounts:Profile') + '#account-tab-support'