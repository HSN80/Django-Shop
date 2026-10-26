from django.urls import path
from . import views

app_name = 'userfav'

urlpatterns = [
    path('create/',views.FavoriteCreate.as_view(),name='Userfav_create'),
    path('<int:pk>/delete/',views.FavoriteDelete.as_view(),name='Userfav_delete'),    
]
