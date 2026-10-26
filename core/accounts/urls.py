from django.urls import path, include
from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('profile/',views.ProfileView.as_view(),name='Profile'),
    path('signup/',views.RegisterView.as_view(),name='Register'),
    path('profile/delete/',views.UserDeleteView.as_view(),name='Delete'),
    path('verify-email/<str:uidb64>/<str:token>/',views.VerifyEmailView.as_view(),name='Verify_email'),
    path('',include('accounts.password_urls')),

]