from django import forms
from .models import Ticket, Message

class TicketCreateForm(forms.ModelForm):

    """
    Form for opening a new support ticket.

    Collects the subject, the department and a description of the problem. The
    owner and the initial status are not part of the form and must be set by the
    view.
    
    Note:
        The widgets limit the subject to 24 and the description to 255
        characters in the browser. Keep these values in sync with the
        ``max_length`` of the ``Ticket`` model fields.
    """

    class Meta:
        model = Ticket
        fields = ['subject', 'department', 'content']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject',
                'maxlength': 24,
            }),
            'department': forms.Select(attrs={
                'class': 'form-select',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your issue',
                'maxlength': 255,
            }),
        }

class MessageCreateForm(forms.ModelForm):

    """
    Form for writing a reply in a ticket conversation.

    Collects only the message text. The ticket and the sender are not part of the
    form and must be set by the view before saving.
    """

    class Meta:
        model = Message
        fields = ['message']
        widgets = {
            'message': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Type your reply...',
            }),
        }
