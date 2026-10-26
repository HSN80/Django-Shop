from datetime import datetime, time, timedelta
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from carts.models import Cart, CartItem
from orders.models import Invoice, Order
from products.models import Catalog, Comment
from tickets.models import Ticket

"""
Data for the admin dashboard.

``build_dashboard`` gathers the summary cards, chart data and "needs
attention" tables shown on the admin index page for superusers.
"""

"""Stock level at or below which a published product counts as low on stock."""
LOW_STOCK = 5

"""
Ticket statuses that need a staff reply: ``open`` and ``progress``.

``reply`` is excluded because staff have already answered and the user is
expected to respond.
"""
TICKET_PENDING = ('open', 'progress')


def _money(value):

    """
    Format an amount in Toman with thousands separators, e.g. ``'1,500 تومان'``.

    ``None`` is treated as 0 and decimals are dropped.
    """

    return f'{int(value or 0):,} تومان'


def _day_start(day):
    
    """
    Return midnight at the start of ``day`` as a timezone-aware datetime.

    The current Django time zone is used.
    """

    return timezone.make_aware(datetime.combine(day, time.min))


def build_dashboard():

    """
    Collect everything the admin dashboard shows.

    Sales figures count only paid orders (``Order.PAID_STATUSES``), dated by the
    order's creation date. The internal ``system`` user is excluded from user
    counts.
    
    Returns:
        A dict with these keys:
    
        * ``cards``: summary cards (today's sales with a comparison to
          yesterday, 30-day sales, orders waiting to ship, tickets needing a
          reply, comments awaiting approval, new users in the last 7 days and
          abandoned carts), each with ``label``, ``value``, ``sub``, ``url`` and
          an optional ``warn`` flag.
        * ``sales_chart``: daily revenue and order counts for the last 30 days,
          with zeros for days without sales.
        * ``status_chart``: number of orders per status (all time).
        * ``to_ship``, ``tickets``, ``low_stock``, ``top_products``: lazy
          querysets for the tables (up to 8, 8, 8 and 5 rows) plus the
          ``*_url`` links to the matching admin lists.
    
    Note:
        Runs many queries, so it is only called for superusers on the admin
        index page. A "yesterday" comparison is shown only if yesterday had
        sales.
    """

    now = timezone.now()
    today = timezone.localdate()
    today_start = _day_start(today)
    yesterday_start = _day_start(today - timedelta(days=1))
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)

    paid = Order.objects.filter(status__in=Order.PAID_STATUSES)

    today_sales = paid.filter(created_date__gte=today_start).aggregate(
        total=Sum('price'), n=Count('id'))
    yesterday_total = paid.filter(
        created_date__gte=yesterday_start, created_date__lt=today_start,
    ).aggregate(total=Sum('price'))['total'] or 0
    month_sales = paid.filter(created_date__gte=month_ago).aggregate(
        total=Sum('price'), n=Count('id'))

    today_total = today_sales['total'] or 0
    today_parts = [f"{today_sales['n']} سفارش"]
    if yesterday_total:
        diff = round((today_total - yesterday_total) * 100 / yesterday_total)
        today_parts.append(f'{diff:+d}٪ نسبت به دیروز')

    to_ship = Order.objects.filter(status='checkout')
    tickets_pending = Ticket.objects.filter(status__in=TICKET_PENDING)
    comments_pending = Comment.objects.filter(status='pending')
    users = User.objects.exclude(username='system')
    abandoned = Cart.objects.filter(status='abandoned')
    abandoned_value = CartItem.objects.filter(cart__status='abandoned').aggregate(
        total=Sum(ExpressionWrapper(
            F('quantity') * Coalesce('price', 'product__price'),
            output_field=DecimalField(max_digits=15, decimal_places=0),
        ))
    )['total']

    orders_url = reverse('admin:orders_order_changelist')
    tickets_url = reverse('admin:tickets_ticket_changelist') + '?status__in=' + ','.join(TICKET_PENDING)
    comments_url = reverse('admin:products_comment_changelist') + '?status__exact=pending'
    carts_url = reverse('admin:carts_cart_changelist') + '?status__exact=abandoned'
    users_url = reverse('admin:accounts_user_changelist')

    to_ship_count = to_ship.count()
    tickets_count = tickets_pending.count()
    comments_count = comments_pending.count()

    cards = [
        {'label': 'فروش امروز', 'value': _money(today_total),
         'sub': ' · '.join(today_parts), 'url': orders_url},
        {'label': 'فروش ۳۰ روز اخیر', 'value': _money(month_sales['total']),
         'sub': f"{month_sales['n']} سفارش", 'url': orders_url},
        {'label': 'منتظر ارسال', 'value': to_ship_count,
         'sub': 'سفارش پرداخت‌شده', 'url': orders_url + '?status__exact=checkout',
         'warn': to_ship_count > 0},
        {'label': 'تیکت نیازمند پاسخ', 'value': tickets_count,
         'sub': 'جدید یا پاسخ کاربر', 'url': tickets_url, 'warn': tickets_count > 0},
        {'label': 'نظر در انتظار تأیید', 'value': comments_count,
         'sub': 'منتظر بررسی', 'url': comments_url, 'warn': comments_count > 0},
        {'label': 'کاربر جدید (۷ روز)', 'value': users.filter(created_date__gte=week_ago).count(),
         'sub': f'از کل {users.count()} کاربر', 'url': users_url},
        {'label': 'سبد رهاشده', 'value': abandoned.count(),
         'sub': _money(abandoned_value), 'url': carts_url},
    ]

    days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    rows = (
        paid.filter(created_date__gte=_day_start(days[0]))
        .annotate(day=TruncDate('created_date'))
        .values('day')
        .annotate(total=Sum('price'), n=Count('id'))
        .order_by('day')
    )
    by_day = {row['day']: row for row in rows}
    sales_chart = {
        'labels': [d.strftime('%m-%d') for d in days],
        'revenue': [(by_day.get(d) or {}).get('total') or 0 for d in days],
        'orders': [(by_day.get(d) or {}).get('n') or 0 for d in days],
    }

    status_names = dict(Order.STATUS_CHOICE)
    status_rows = Order.objects.order_by().values('status').annotate(n=Count('id'))
    status_chart = {
        'labels': [str(status_names.get(r['status'], r['status'])) for r in status_rows],
        'data': [r['n'] for r in status_rows],
    }

    return {
        'cards': cards,
        'sales_chart': sales_chart,
        'status_chart': status_chart,
        'to_ship': to_ship.select_related('profile__user').order_by('created_date')[:8],
        'to_ship_url': orders_url + '?status__exact=checkout',
        'tickets': tickets_pending.select_related('profile__user').order_by('updated_date')[:8],
        'tickets_url': tickets_url,
        'low_stock': Catalog.objects.filter(
            status=Catalog.Status.PUBLISHED, stock__lte=LOW_STOCK,
        ).order_by('stock', 'title')[:8],
        'low_stock_url': reverse('admin:products_catalog_changelist') + '?status__exact=PB',
        'top_products': Invoice.objects.filter(
            order__status__in=Order.PAID_STATUSES, order__created_date__gte=month_ago,
        ).values('product_id', 'product__title').annotate(qty=Sum('quantity')).order_by('-qty')[:5],
    }