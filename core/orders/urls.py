from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.OrderView.as_view(), name='checkout'),
    path('review/', views.OrderReview.as_view(), name='review'),
    path('<int:pk>/pay/', views.PaymentStartView.as_view(), name='pay'),
    path('verify/', views.PaymentVerifyView.as_view(), name='verify'),
    path('payment/<int:pk>/', views.PaymentResultView.as_view(), name='result'),
]