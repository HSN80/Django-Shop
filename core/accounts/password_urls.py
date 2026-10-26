from django.urls import path
from . import password_views as views


"""
URL routes for authentication and password management.

Covers login and logout, changing a password while logged in, and the
password-reset flow (request, confirmation email sent, reset link, and
completion). The views live in ``password_views``.
"""

urlpatterns = [
    path('login/',views.UserLoginView.as_view(),name='Login'),
    path('logout/',views.UserLogoutView.as_view(),name='Logout'),
    path('password-change/',views.UserPasswordChangeView.as_view(),name='Password_change'),
    path('password-reset/',views.UserPasswordResetView.as_view(),name='Password_reset'),
    path('password-reset-done/',views.UserPasswordResetDoneView.as_view(),name='Password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',views.UserPasswordResetConfirmView.as_view(),name='Password_reset_confirm'),
    path('password-reset-complete/',views.UserPasswordResetCompleteView.as_view(),name='Password_reset_complete'),
    
]