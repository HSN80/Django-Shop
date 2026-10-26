from django.shortcuts import redirect
from django.contrib.auth import mixins
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme

"""
Access-control mixins for the accounts app.

``IsVerifiedMixin`` restricts a view to logged-in, verified users.
``AnonymousUserMixin`` keeps logged-in users away from views meant for
anonymous visitors, such as login and registration.
"""

class IsVerifiedMixin(mixins.UserPassesTestMixin):

    """
    Allow only authenticated users whose account is verified.

    Add it to a class-based view. Users who fail the check are redirected with a
    message instead of receiving a 403 response.
    """

    def test_func(self):

        """Return ``True`` if the user is logged in and ``is_verified`` is set."""

        user = self.request.user
        return user.is_authenticated and user.is_verified
    
    def handle_no_permission(self):

        """
        Redirect users who failed the check, with an explanatory message.

        Anonymous users are sent to the login page with an error message.
        Authenticated but unverified users are sent to their profile with a warning.

        Returns:
            A redirect response.

        Note:
            The warning mentions verifying the email, although verification is
            tracked by the single ``is_verified`` flag.
        """

        if not self.request.user.is_authenticated:
            messages.error(self.request, 'please login to your account first.')
            return redirect('accounts:Login')

        elif self.request.user.is_authenticated and not self.request.user.is_verified:
            messages.warning(self.request, 'please verify your email first')
            return redirect('products:Catalog_list')
    
class AnonymousUserMixin:

    """
    Redirect already logged-in users away from a view.

    Meant for views such as login and registration. Anonymous users continue to
    the view as usual.

    Attributes:
        default_redirect_url: Where to send a logged-in user when no safe
            redirect target is found. Defaults to ``'/'``.
    """

    default_redirect_url = '/'

    def dispatch(self, request, *args, **kwargs):


        """
        Redirect authenticated users; pass anonymous users on to the view.

        For an authenticated user, adds an info message and picks a target in this
        order: the ``next`` parameter (GET or POST), then the ``Referer`` header, then
        ``default_redirect_url``.

        Args:
            request: The current request.
            *args: Positional arguments passed on to the view.
            **kwargs: Keyword arguments passed on to the view.

        Returns:
            A redirect for authenticated users, otherwise the normal view response.

        Note:
            A target is used only if it points to the same host (and uses HTTPS when
            the request does) and is not the current path; otherwise
            ``default_redirect_url`` is used. This avoids open redirects and
            redirect loops.
        """
        
        if request.user.is_authenticated:
            messages.info(request, 'you already loged in.')

            redirect_to = request.GET.get('next') or request.POST.get('next')

            if not redirect_to:

                redirect_to = request.META.get('HTTP_REFERER')

            current_path = request.path

            is_safe_url = redirect_to and url_has_allowed_host_and_scheme(
                url=redirect_to,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            )

            if is_safe_url and redirect_to != current_path:

                return redirect(redirect_to)
            
            return redirect(self.default_redirect_url)
        
        return super().dispatch(request, *args, **kwargs)
    
class StaffRequiredMixin(mixins.UserPassesTestMixin):
       """Allow only staff users; anonymous users are sent to the login page."""

       def test_func(self):
           return self.request.user.is_staff
