from django.shortcuts import redirect
from django.db.models import Q
from django.db import transaction
from django.core.paginator import Paginator
from django.views.generic import UpdateView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views import View
from django.contrib import messages
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from .models import Profile
from .forms import ProfileModelForm, CustomUserRegisterationForm, UserModelForm
from .mixins import AnonymousUserMixin, IsVerifiedMixin
from tickets.froms import TicketCreateForm

# Create your views here.

User = get_user_model()

class ProfileView(IsVerifiedMixin,UpdateView):

    """
    Display and update the authenticated user's profile and related data.

    Manages a dual-form setup (``ProfileModelForm`` and ``UserModelForm``) and
    provides filtered, paginated order history with search capabilities.
    """

    template_name = 'accounts/account.html'
    form_class = ProfileModelForm
    second_form_class = UserModelForm
    success_url = reverse_lazy('accounts:Profile')

    def get_queryset(self):

        """
        Optimize database queries for the user profile and related relations.

        Prefetches orders, invoices, comments, favorites, and cart items using
        ``select_related`` and ``prefetch_related`` to prevent N+1 query issues.

        Returns:
            QuerySet: The pre-optimized ``Profile`` queryset.
        """

        return Profile.objects.select_related('user').prefetch_related(
            'order',
            'order__invoices',
            'comments',
            'favorites',
            'carts__cart_items'
        ).all()
    
    def get_object(self, queryset=None):

        """
        Retrieve the profile instance belonging to the current user.

        Args:
            queryset: Optional custom queryset; defaults to ``get_queryset()``.

        Returns:
            Profile: The profile instance for ``self.request.user``.
        """

        queryset = self.get_queryset()
        return queryset.get(user=self.request.user)
    
    def get_context_data(self, **kwargs):

        """
        Build context data for the profile dashboard template.

        Handles order filtering by status, search queries (by ID, postal code,
        name, or product title), pagination with elided page ranges, secondary user
        form instantiation, and the ticket creation form.

        Args:
            **kwargs: Extra context keyword arguments.

        Returns:
            dict: The populated context dictionary.
        """

        context = super().get_context_data(**kwargs)
        
        orders = self.object.order.all().order_by('-created_date')
        
        search_query = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', 'all')

        if status_filter != 'all':
            orders = orders.filter(status=status_filter)

        if search_query:
            clean_query = search_query.replace('#ORD-', '')
            
            if clean_query.isdigit():
                orders = orders.filter(Q(id=clean_query) | Q(postal_code__icontains=clean_query))
            else:
                orders = orders.filter(
                    Q(first_name__icontains=clean_query) |
                    Q(last_name__icontains=clean_query) |
                    Q(cart__cart_items__product__title__icontains=clean_query)
                ).distinct() 

        if self.request.POST:
            context['second_form'] = UserModelForm(self.request.POST,instance=self.object.user)
        else:
            context['second_form'] = UserModelForm(instance=self.object.user)

        paginator = Paginator(orders, 5) 
        page_number = self.request.GET.get('page')
        orders_page_obj = paginator.get_page(page_number)
        
        page_range = paginator.get_elided_page_range(
            number=orders_page_obj.number, 
            on_each_side=1, 
            on_ends=1
        )
        
        context['orders_page_obj'] = orders_page_obj
        context['page_range'] = page_range
        context['current_status'] = status_filter
        context['search_query'] = search_query
        context['ticket_form'] = TicketCreateForm()

        return context
    
    def form_valid(self, form):

        """
        Save both the profile and user forms atomically within a transaction.

        If the secondary user form is invalid, re-renders the page with errors;
        otherwise, commits changes and redirects to the success URL.

        Args:
            form: The valid main profile form instance.

        Returns:
            HttpResponse: A redirect on success or rendered response with errors.
        """

        context = self.get_context_data()
        second_form = context['second_form']

        with transaction.atomic():
            self.object = form.save()

            if second_form.is_valid():
                second_form.save()
            else:
                return self.render_to_response(self.get_context_data(form=form))
            
        return super().form_valid(form)
    
    
class UserDeleteView(LoginRequiredMixin,DeleteView):

    """
    Handle deletion of the authenticated user's account.

    Restricts access to logged-in users and limits deletion strictly to the
    currently authenticated user instance.
    """

    model = User
    success_url = '/'
    template_name = 'accounts/delete.html'

    def get_object(self, queryset=None):
        
        """
        Retrieve the user instance targeted for deletion.

        Args:
            queryset: Optional custom queryset; defaults to the base model queryset.

        Returns:
            User: The currently authenticated user instance.
        """

        queryset = self.get_queryset()
        return queryset.get(id=self.request.user.id)


class RegisterView(AnonymousUserMixin,CreateView):
    
    """
    Handle new user registration.

    Restricts access to anonymous users using ``AnonymousUserMixin`` and uses
    ``CustomUserRegisterationForm`` to create new accounts.
    """

    model = User
    success_url = reverse_lazy('accounts:Login')
    template_name = 'registration/register.html'
    form_class = CustomUserRegisterationForm

class VerifyEmailView(View):

    """
    Verify a user's email address via a token-based link sent upon registration.

    Decodes the user ID from ``uidb64`` and validates the verification token.
    """

    def get(self, request, uidb64, token, *args, **kwargs):

        """
        Process GET requests for email verification links.

        Decodes the user ID, checks token validity, activates the user's verification
        status if valid, and displays appropriate feedback messages before redirecting.

        Args:
            request: The HTTP request object.
            uidb64: Base64-encoded primary key of the user.
            token: The token generated for email verification.

        Returns:
            HttpResponseRedirect: Redirects to the login page with a success, info,
                or error message.
        """

        try:

            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and user.is_verified:

            messages.info(request, 'your account allready verified,\n please login to your account.')
            return redirect('accounts:Login')
        
        if user is not None and default_token_generator.check_token(user, token):

            user.is_verified = True
            user.save()
            messages.success(request, 'your account has been successfully verified\n please login to your account.')
            return redirect('accounts:Login')
        
        else:

            messages.error(request, 'this link is wrong or expierd.')
            return redirect('accounts:Login')

        