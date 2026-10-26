from django.contrib import admin
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from simple_history.admin import SimpleHistoryAdmin
from .models import Cart, CartItem

# Register your models here.

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    can_delete = False
    fields = ('product', 'quantity', 'price')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):

        """Restricts adding new cart items directly from the parent cart admin form."""
        
        return False


@admin.register(Cart)
class CartAdmin(SimpleHistoryAdmin):

    """Admin configuration for carts with custom database annotations for total items and calculated cart value."""

    list_display = ('id', 'profile', 'status', 'items_total', 'cart_total', 'updated_date')
    list_filter = ('status', 'updated_date')
    search_fields = ('profile__user__username', 'profile__user__phone')
    list_select_related = ('profile__user',)
    inlines = [CartItemInline]

    def get_queryset(self, request):

        """Annotates the queryset with total item count and dynamically computed price, falling back to product prices."""

        line = ExpressionWrapper(
            F('cart_items__quantity')
            * Coalesce('cart_items__price', 'cart_items__product__price'),
            output_field=DecimalField(max_digits=15, decimal_places=0),
        )
        return super().get_queryset(request).annotate(
            items_total=Sum('cart_items__quantity'),
            cart_total=Sum(line),
        )

    @admin.display(description='تعداد اقلام', ordering='items_total')
    def items_total(self, obj):
        return obj.items_total or 0

    @admin.display(description='جمع سبد', ordering='cart_total')
    def cart_total(self, obj):

        """Formats the calculated cart total integer with thousand separators."""

        return f'{obj.cart_total or 0:,}'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'price')
    list_select_related = ('cart__profile__user', 'product')