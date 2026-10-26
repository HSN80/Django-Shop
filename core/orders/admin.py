from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Order, Invoice, Payment

# Register your models here.

"""
order management (filters, search, invoice lines inside the order
page and bulk "sent" / "arrived" actions) and a read-mostly invoice list.
Every status change goes through ``save()``, so it is recorded in history.
"""

class InvoiceInline(admin.TabularInline):
    
    """
    Read-only table of an order's invoice lines, shown on the order page.

    Lines cannot be added, edited or deleted from here.
    """

    model = Invoice
    extra = 0
    can_delete = False
    fields = ('product', 'quantity', 'purchase_price')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):

        """Disallow adding invoice lines from the order page."""
        
        return False


@admin.register(Order)
class OrderAdmin(SimpleHistoryAdmin):

    """
    Admin for ``Order`` with change history, filters and status actions.

    The buyer, cart, price and timestamps are read-only, so an order's financial
    data cannot be edited from the admin. Invoice lines appear inline.
    """

    list_display = (
        'id', 'full_name', 'profile', 'price', 'status',
        'tracking_code', 'created_date',
    )
    list_filter = ('status', 'created_date')
    search_fields = (
        'tracking_code', 'first_name', 'last_name', 'postal_code',
        'profile__user__phone', 'profile__user__username',
    )
    list_select_related = ('profile__user',)
    date_hierarchy = 'created_date'
    ordering = ('-created_date',)
    readonly_fields = ('profile', 'cart', 'price', 'created_date', 'updated_date')
    inlines = [InvoiceInline]
    actions = ['mark_sent', 'mark_arrived']

    @admin.display(description='نام')
    def full_name(self, obj):

        """Show the recipient's first and last name in one column."""
        
        return f'{obj.first_name} {obj.last_name}'

    def _move(self, request, queryset, src, dst, need_code=False):

        """
        Move eligible orders from one status to another (bulk-action helper).

        Args:
            request: The current admin request.
            queryset: The selected orders.
            src: Only orders currently in this status are changed.
            dst: The status to set.
            need_code: If ``True``, orders without a tracking code are skipped too.

        Note:
            Orders are saved one by one with a change reason, so each change is
            recorded in history. Ineligible orders are skipped and counted in the
            message shown to the admin.
        """

        orders = queryset.filter(status=src)
        if need_code:
            orders = orders.exclude(tracking_code__isnull=True).exclude(tracking_code='')
        done = 0
        for order in orders:
            order.status = dst
            order._change_reason = 'تغییر وضعیت از لیست ادمین'
            order.save(update_fields=['status', 'updated_date'])
            done += 1
        skipped = queryset.count() - done
        self.message_user(
            request,
            f'{done} سفارش تغییر کرد، {skipped} سفارش رد شد (وضعیت یا کد رهگیری مناسب نبود).',
        )

    @admin.action(description='ثبت به‌عنوان ارسال‌شده (پرداخت‌شده‌ها با کد رهگیری)')
    def mark_sent(self, request, queryset):

        """
        Mark paid orders as sent.

        Only orders in ``checkout`` status that already have a tracking code are
        changed; all others are skipped.
        """

        self._move(request, queryset, 'checkout', 'sent', need_code=True)

    @admin.action(description='ثبت به‌عنوان تحویل‌شده (ارسال‌شده‌ها)')
    def mark_arrived(self, request, queryset):

        """Mark sent orders as arrived (only orders in ``sent`` status are changed)."""

        self._move(request, queryset, 'sent', 'arrived')


@admin.register(Invoice)
class InvoiceAdmin(SimpleHistoryAdmin):
    
    """Admin for ``Invoice`` lines with search by product and tracking code."""

    list_display = ('id', 'order', 'product', 'quantity', 'purchase_price', 'created_date')
    list_select_related = ('order__profile__user', 'product')
    search_fields = ('product__title', 'order__tracking_code')
    list_filter = ('created_date',)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order', 'track_id', 'amount_toman', 'status',
        'ref_number', 'paid_date', 'created_date',
    )
    list_filter = ('status', 'created_date')
    search_fields = ('track_id', 'ref_number', 'order__tracking_code')
    list_select_related = ('order__profile__user',)

    @admin.display(description='مبلغ (تومان)', ordering='amount')
    def amount_toman(self, obj):
        return f'{obj.amount // 10:,}'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False