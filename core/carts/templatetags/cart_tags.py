from django import template
from ..models import Cart

register = template.Library()

@register.filter
def cart_item_count(user):
    active_cart = Cart.objects.filter(
        profile = user.profile,
        status = 'active',
    ).first()

    if active_cart:
        return active_cart.items_count
    
    return 0

@register.simple_tag
def get_active_cart(user):
    active_cart = Cart.objects.filter(
        profile = user.profile,
        status__in = ['active','empty'],
    ).first()

    if active_cart:
        return active_cart
    
    return None

