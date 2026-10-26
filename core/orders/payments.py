"""Payment workflow: start a gateway payment, verify it and complete the order."""
import logging

from django.db import transaction
from django.utils import timezone

from products.models import Catalog
from .models import Invoice, Payment
from carts.models import Cart
from .zibal import ALREADY_VERIFIED, OK_RESULT, GatewayError, ZibalGateway, to_gateway_mobile

logger = logging.getLogger(__name__)

TOMAN_TO_RIAL = 10  # prices are in Toman, the gateway works in Rials


def stock_shortages(order):
    """Return the titles of products whose stock no longer covers the order's cart."""
    if order.cart_id is None:
        return []
    items = order.cart.cart_items.select_related('product')
    return [item.product.title for item in items if item.product.stock < item.quantity]


def start_payment(order, callback_url):
    """Create a ``Payment`` for the order and return the gateway URL to redirect to.

    Raises:
        GatewayError: If the gateway cannot be reached or rejects the request.
            The payment is then marked as failed.
    """
    payment = Payment.objects.create(order=order, amount=order.price * TOMAN_TO_RIAL)
    gateway = ZibalGateway()
    try:
        payment.track_id = gateway.request(
            amount=payment.amount,
            order_id=payment.pk,
            callback_url=callback_url,
            mobile=to_gateway_mobile(order.profile.user.phone),
            description=f'سفارش {order.pk}',
        )
    except GatewayError:
        payment.status = Payment.FAILED
        payment.save(update_fields=['status', 'updated_date'])
        raise
    payment.save(update_fields=['track_id', 'updated_date'])
    return gateway.start_url(payment.track_id)


def fulfill_order(order):
    """Create the invoice lines, reduce stock and mark the order and its cart as paid.

    Must run inside a transaction. If a product sold out in the meantime the
    sale is still recorded (the customer has paid) and an error is logged so
    the shop can handle it by hand.
    """
    cart = order.cart
    if cart is not None:
        items = list(cart.cart_items.all())
        products = {
            product.pk: product
            for product in Catalog.objects.select_for_update().filter(
                pk__in=[item.product_id for item in items]
            )
        }
        for item in items:
            product = products[item.product_id]
            Invoice.objects.create(
                order=order,
                product=product,
                quantity=item.quantity,
                purchase_price=product.final_price,  # price of one unit
            )
            if product.stock < item.quantity:
                logger.error(
                    'Oversold product %s on order %s: stock %s, sold %s',
                    product.pk, order.pk, product.stock, item.quantity,
                )
            product.stock = max(product.stock - item.quantity, 0)
            product._change_reason = f'فروش سفارش #{order.pk}'
            product.save(update_fields=['stock', 'updated_date'])

        cart.status = 'checkout'
        cart._change_reason = f'پرداخت سفارش #{order.pk}'
        cart.save(update_fields=['status', 'updated_date'])
    else:
        logger.error('Order %s has no cart; no invoice lines were created', order.pk)

    order.status = 'checkout'
    order._change_reason = 'پرداخت موفق (زیبال)'
    order.save(update_fields=['status', 'updated_date'])

def cancel_order(order):
    """Cancel an unpaid order and give its cart back to the customer.

    The cart becomes active again, unless the customer already has another
    active cart (only one is allowed); then it is marked as abandoned.
    """
    order.status = 'canceled'
    order._change_reason = 'لغو سفارش: پرداخت انجام نشد'
    order.save(update_fields=['status', 'updated_date'])

    cart = order.cart
    if cart is None:
        return
    has_active = Cart.objects.filter(profile_id=cart.profile_id, status='active').exists()
    cart.status = 'abandoned' if has_active else 'active'
    cart._change_reason = 'بازگشت سبد پس از پرداخت ناموفق'
    cart.save(update_fields=['status', 'updated_date'])

def verify_payment(track_id):
    """Verify a payment with the gateway and, if it succeeded, complete the order.

    Safe to call many times: a payment that was already processed is returned
    unchanged, so refreshing the callback page never duplicates invoices.

    Returns:
        The ``Payment``, or ``None`` if no payment has this ``track_id``.

    Raises:
        GatewayError: If the gateway cannot be reached. The payment stays
            pending and can be verified again later.
    """
    payment = Payment.objects.filter(track_id=track_id).first()
    if payment is None or payment.status != Payment.PENDING:
        return payment

    data = ZibalGateway().verify(track_id)  # network call, kept outside the transaction
    succeeded = (
        data.get('result') in (OK_RESULT, ALREADY_VERIFIED)
        and data.get('amount', payment.amount) == payment.amount
    )

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != Payment.PENDING:  # another request finished first
            return payment

        payment.gateway_status = data.get('status')
        if succeeded:
            payment.status = Payment.PAID
            payment.ref_number = str(data.get('refNumber') or '')
            payment.card_number = data.get('cardNumber') or ''
            payment.paid_date = timezone.now()
            fulfill_order(payment.order)
        else:
            payment.status = Payment.FAILED
            gateway_says_paid = data.get('result') in (OK_RESULT, ALREADY_VERIFIED)
            # only cancel when the gateway is sure it was not paid; if it says
            # paid but the amount differs, money was taken, so keep the order
            if not gateway_says_paid and payment.order.status == 'awaiting':
                cancel_order(payment.order)
        payment.save()
    return payment