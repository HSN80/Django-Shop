from django.urls import path
from . import views

app_name = 'carts'

urlpatterns = [
    path('create/',views.AddToCartView.as_view(),name='Cart_item_create'),
    path('<int:pk>/delete/',views.DeleteFromCartView.as_view(),name='Cart_item_delete'),
    path('cancel/<int:pk>/',views.CancelCartView.as_view(),name='Cart_cancel')
]
