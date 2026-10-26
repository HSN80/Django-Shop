from django.urls import path
from . import comment_views as views


urlpatterns = [
    path('create/',views.CommentCreateView.as_view(),name='Comment_create'),
    path('<int:pk>/delete/',views.CommentDelete.as_view(),name='Comment_delete'),
]
