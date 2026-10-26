from django.contrib.auth import views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy

"""
Authentication and password views for the accounts app.

Thin subclasses of Django's built-in auth views that only set the templates
and redirect targets used by this project.
"""

class UserLoginView(views.LoginView):

    """
    Log a user in with the ``registration/login.html`` template.

    Users who are already logged in are redirected away instead of seeing the
    form again.
    """

    template_name = 'registration/login.html'
    redirect_authenticated_user = True


class UserLogoutView(views.LogoutView):

    """
    Log the user out and redirect to the login page.

    Note:
        Since Django 5.0 logging out requires a POST request, so the logout
        control in the templates must be a form, not a plain link.
    """

    next_page = reverse_lazy('accounts:Login')
    
     
class UserPasswordChangeView(LoginRequiredMixin,views.PasswordChangeView):

    """
    Let a logged-in user change their password.

    Requires login. After a successful change the user is sent to the catalog
    list with a success message.
    """

    template_name = 'registration/passwordchange.html'
    # success_url = reverse_lazy('products:Catalog_list')
    
    def get_success_url(self):

        """
        Return the catalog list URL and queue a success message.

        Returns:
            The URL of the catalog list.

        Note:
            The message is added here, so this method must be called only once,
            after the password has been changed.
        """

        messages.success(self.request,'your password has changed.')
        return reverse_lazy('products:Catalog_list')

class UserPasswordResetView(views.PasswordResetView):

    """
    Ask for an email address and send a password reset link to it.

    Uses a custom email template and redirects to the "email sent" page.

    Note:
        Django sends the email to every active user with a matching address.
        Since ``User.email`` is not unique, several accounts sharing an email
        each receive their own reset link.
    """

    template_name = 'registration/password_reset.html'
    email_template_name = 'registration/password_reset_email.html'
    success_url = reverse_lazy('accounts:Password_reset_done')



class UserPasswordResetDoneView(views.PasswordResetDoneView):

    """Tell the user that a password reset email has been sent."""

    template_name = 'registration/password_reset_done.html'


class UserPasswordResetConfirmView(views.PasswordResetConfirmView):

    """
    Let the user choose a new password through the link from the reset email.

    Redirects to the "reset complete" page on success.
    """

    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:Password_reset_complete')



class UserPasswordResetCompleteView(views.PasswordResetCompleteView):

    """Tell the user that the password has been reset successfully."""
    
    template_name = 'registration/password_reset_complite.html'