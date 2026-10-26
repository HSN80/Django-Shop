from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('create/',views.TicketCreateView.as_view(),name='Ticket_create'),
    path('create/<int:ticket_id>/reply/',views.MessageCreateView.as_view(),name='Message_create')
    
]
