from django.shortcuts import redirect, get_object_or_404
from django.db import transaction
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from carts.templatetags.cart_tags import get_active_cart
from .models import Order, Payment
from .froms import OrderModelForm
from .payments import start_payment, stock_shortages, verify_payment
from .zibal import GatewayError

# Create your views here.

def parse_address(address):

    """
    Split a stored address into state, city and street.

    Expects the ``"<state>, <city>, <street>"`` format produced by
    ``ProfileModelForm.clean``.

    Args:
        address: The address string saved on the profile (may be empty).

    Returns:
        A list ``[state, city, street]``, or ``None`` if the address is empty or
        has fewer than three comma-separated parts.

    Note:
        Only the first two ``", "`` separators are used, so any further commas
        stay inside the street part.

    """

    if not address:
        return None
    parts = address.split(', ',2)
    return parts if len(parts) >= 3 else None 

class OrderView(LoginRequiredMixin,CreateView):

    """
    Checkout page: collect the delivery details and create the order.

    Requires login and a non-empty active cart. The form is pre-filled with the
    state, city and street parsed from the profile's saved address.
    """

    model = Order
    form_class = OrderModelForm
    template_name = 'orders/checkout.html'
    
    def dispatch(self, request, *args, **kwargs):

        """
        Load the user's active cart, or redirect if there is nothing to order.

        An empty or missing cart redirects to the wallet tab of the profile page
        with an error message. Otherwise the cart is kept on ``self.cart``.
        """

        cart = get_active_cart(request.user)
        
        if not cart or cart.items_count == 0:
            messages.error(request,'سبد شما خالی است.')
            return redirect(reverse('accounts:Profile') + '#account-tab-wallet')
        
        self.cart = cart

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        """
        Add the cart and the previous state, city and address to the context.

        After a failed submission the values the user just typed are returned. On a
        fresh page they come from the profile's saved address; if that cannot be
        parsed, the whole address is used as the street and the state and city are
        left empty.
        """

        context = super().get_context_data(**kwargs)
        context['cart'] = self.cart

        form = context['form']
        if form.is_bound:

            previous_state = form.data.get('state_select', '')
            previous_city = form.data.get('city_select', '')
            previous_address = form.data.get('address', '')

        else:

            parsed = parse_address(self.cart.profile.address)

            if parsed:

                previous_state, previous_city, previous_address = parsed

            else:

                previous_state, previous_city = '', ''
                previous_address = self.cart.profile.address or ''

        context['previous_state'] = previous_state
        context['previous_city'] = previous_city
        context['previous_address'] = previous_address

        return context

    def form_valid(self, form):

        """
        Create the order from the valid form and take the cart out of 'active'.

        Links the order to the buyer's profile and cart, sets its price from the
        cart total, saves it once and moves the cart to ``updating``. Both writes
        happen in one transaction, so a failed save leaves the cart untouched.
        """

        with transaction.atomic():
            form.instance.profile = self.cart.profile
            form.instance.cart = self.cart
            form.instance.price = self.cart.total_price
            response = super().form_valid(form)
            self.cart.status = 'updating'
            self.cart.save(update_fields=['status'])
        return response

    def get_success_url(self):

        """Send the buyer to the payment step of the order that was just created."""

        return reverse('orders:pay', args=[self.object.pk])

class OrderReview(LoginRequiredMixin,TemplateView):

    """
    Review page shown before payment.

    Displays the cart together with the buyer's name, postal code and the address
    split into state, city and street. Requires login and a non-empty active cart.
    """

    template_name = 'orders/review.html'

    def dispatch(self, request, *args, **kwargs):

        """
        Check that the order can be reviewed, or redirect to fix it.

        An empty or missing cart redirects to the profile's wallet tab with an error
        message. If the profile lacks a first name, last name, postal code or a
        parsable address, the user is sent to the checkout page to fill them in.
        Otherwise the cart and the parsed address are kept on the view.
        """

        cart = get_active_cart(request.user)
        if not cart or cart.items_count == 0:
            messages.error(request,'سبد شما خالی است.')
            return redirect(reverse('accounts:Profile') + '#account-tab-wallet')
        
        profile = cart.profile
        parsed = parse_address(profile.address)

        if not all([profile.first_name, profile.last_name, profile.postal_code, parsed]):
            return redirect('orders:checkout')

        self.cart = cart
        self.parsed_address = parsed    

        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):

        """
        Add the cart, the profile and the address parts to the context.

        The address is exposed as ``state``, ``city`` and ``street``.
        """

        context = super().get_context_data(**kwargs)
        state , city , street = self.parsed_address

        context.update({
            'cart': self.cart,
            'profile': self.cart.profile,
            'state': state,
            'city': city,
            'street': street
        })

        return context

class PaymentStartView(LoginRequiredMixin, View):

    """
    Start a gateway payment for one of the current user's unpaid orders.

    Checks that the order is still waiting for payment and that the stock
    covers it, creates the payment at the gateway and redirects the customer
    to the gateway page. Problems are reported as messages on the profile page.
    """

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, profile=request.user.profile)
        if order.status != 'awaiting':
            messages.info(request, 'این سفارش قبلاً پرداخت شده یا لغو شده است.')
            return redirect('accounts:Profile')

        shortages = stock_shortages(order)
        if shortages:
            messages.error(request, 'موجودی این محصولات کافی نیست: ' + '، '.join(shortages))
            return redirect('accounts:Profile')

        try:
            gateway_url = start_payment(order, request.build_absolute_uri(reverse('orders:verify')))
        except GatewayError as error:
            messages.error(request, str(error))
            return redirect('accounts:Profile')
        return redirect(gateway_url)


class PaymentVerifyView(View):

    """
    Callback page the gateway sends the customer back to.

    Reads ``trackId`` from the query string and verifies the payment with the
    gateway itself (the other callback parameters are not trusted). It does not
    require login, because the session may be lost during the payment; the
    result page afterwards does.
    """

    def get(self, request):
        track_id = request.GET.get('trackId', '')
        if not track_id.isdigit():
            messages.error(request, 'اطلاعات بازگشتی از درگاه معتبر نیست.')
            return redirect('accounts:Profile')

        try:
            payment = verify_payment(int(track_id))
        except GatewayError:
            messages.warning(
                request,
                'بررسی پرداخت انجام نشد. اگر مبلغی از حساب شما کسر شده، '
                'چند دقیقه بعد دوباره بررسی کنید یا با پشتیبانی تماس بگیرید.',
            )
            return redirect('accounts:Profile')

        if payment is None:
            messages.error(request, 'پرداختی با این کد پیدا نشد.')
            return redirect('accounts:Profile')
        return redirect('orders:result', pk=payment.pk)


class PaymentResultView(LoginRequiredMixin, DetailView):

    """Show the outcome of a payment; users can only see their own payments."""

    template_name = 'orders/payment_result.html'
    context_object_name = 'payment'

    def get_queryset(self):
        return Payment.objects.filter(order__profile=self.request.user.profile).select_related('order')
    
