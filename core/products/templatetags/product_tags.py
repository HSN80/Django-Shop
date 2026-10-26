from django import template
from django.db.models import Prefetch
from products.models import Catalog
from carts.models import Cart, CartItem
from accounts.models import Profile
from orders.models import Order

register = template.Library()

@register.inclusion_tag('headers.html',takes_context=True)
def headers_context(context):
    user = context.get('user')

    profile = None
    cart = None
    order = None
    favorites_count = 0
    
    if user and user.is_authenticated:

        profile = Profile.objects.filter(user=user).prefetch_related('favorites').first()

        if profile:
            favorites_count = len(profile.favorites.all())

            cart_query = CartItem.objects.select_related('product').prefetch_related(
                'product__images'
            )

            cart = Cart.objects.prefetch_related(
                Prefetch('cart_items',queryset=cart_query)
            ).filter(profile=profile,status='active').first()

        order = Order.objects.filter(profile=profile).prefetch_related(
        'invoices'
        ).last()
    
    return {
        'user': user,
        'cart': cart,
        'profile': profile,
        'order': order,
        'favorites': favorites_count
    }