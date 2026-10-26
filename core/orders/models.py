from django.db import models
from simple_history.models import HistoricalRecords

# Create your models here.

class Order(models.Model):

    """
    An order placed by a user, created at checkout.

    Attributes:
        STATUS_CHOICE: Available statuses: ``awaiting`` (waiting for payment),
            ``checkout`` (paid), ``canceled``, ``sent`` and ``arrived``.
        PAID_STATUSES: Statuses that count as a completed sale (``checkout``,
            ``sent`` and ``arrived``). Used for sales and spending statistics.
        profile: The buyer. Set to ``NULL`` if the profile is deleted, so the
            order is kept.
        cart: The cart the order was created from (one-to-one). Set to ``NULL``
            if the cart is deleted.
        first_name: Recipient's first name.
        last_name: Recipient's last name.
        address: Delivery address, stored as ``"<state>, <city>, <street>"``.
        postal_code: Delivery postal code.
        price: Total price in Toman.
        tracking_code: Unique shipping tracking code; empty until the order is
            sent.
        status: Current status, ``awaiting`` by default.
        created_date: When the order was placed.
        updated_date: When the order was last saved.

    Note:
        Orders are ordered by creation date, oldest first. The order stores its
        own copy of the recipient details, so later profile edits do not change
        existing orders.
    """

    STATUS_CHOICE = (
        ('awaiting', 'در انتظار پرداخت'),
        ('checkout', 'پرداخت شده'),
        ('canceled', 'لغو شده'),
        ('sent', 'ارسال شده'),
        ('arrived', 'تحویل شده'),
    )

    PAID_STATUSES = ('checkout', 'sent', 'arrived')

    profile = models.ForeignKey(
        'accounts.Profile',
        verbose_name = 'کاربر',
        on_delete = models.SET_NULL,
        related_name = 'order',
        null = True,
        blank = True
    )

    cart = models.ForeignKey(
        'carts.Cart',
        verbose_name = 'سبد',
        on_delete = models.SET_NULL,
        related_name = 'order',
        null = True,
        blank = True
    )

    first_name = models.CharField(verbose_name = 'نام',max_length=24)
    last_name = models.CharField(verbose_name = 'نام خانوادگی',max_length=24)
    address = models.TextField(verbose_name = 'آدرس')
    postal_code = models.CharField(verbose_name = 'کدپستی',max_length=12)

    price = models.PositiveIntegerField(verbose_name = 'قیمت کل')
    tracking_code = models.CharField(
        verbose_name = 'کد رهگیری',
        unique = True,
        null = True,
        blank = True,
        max_length = 24
    )

    status = models.CharField(
        verbose_name = 'وضعیت',
        choices = STATUS_CHOICE,
        default = 'awaiting',
    )

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now = True)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.profile} - {self.price} - {self.get_status_display()}'
    
    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'
        ordering = ('created_date',)

class Invoice(models.Model):

    """
    One product line of an order.

    Attributes:
        order: The order this line belongs to. Set to ``NULL`` if the order is
            deleted.
        product: The purchased product. Protected: a product that appears on an
            invoice cannot be deleted.
        quantity: Number of units bought.
        purchase_price: The price recorded at purchase time. It is a snapshot and
            does not follow later changes to the product's price.
        created_date: When the line was created.
        updated_date: When the line was last saved.
    """

    order = models.ForeignKey(
        'orders.Order',
        verbose_name = 'سفارش',
        on_delete = models.SET_NULL,
        related_name = 'invoices',
        null = True,
        blank = True
    )

    product = models.ForeignKey(
        'products.Catalog',
        verbose_name = 'محصول',
        on_delete = models.PROTECT,
        related_name = 'invoices'
    )

    quantity = models.PositiveIntegerField(verbose_name = 'تعداد')
    purchase_price = models.PositiveIntegerField(verbose_name = 'قیمت خرید')

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now = True)
    history = HistoricalRecords()

    class Meta:

        verbose_name = 'فاکتور'
        verbose_name_plural = 'فاکتور ها'
        ordering = ('created_date',)
        
class Payment(models.Model):

    PENDING, PAID, FAILED = 'pending', 'paid', 'failed'
    STATUS_CHOICE = (
        (PENDING, 'در انتظار'),
        (PAID, 'پرداخت شده'),
        (FAILED, 'ناموفق'),
    )

    order = models.ForeignKey(
        'orders.Order',
        verbose_name = 'سفارش',
        on_delete = models.PROTECT,
        related_name = 'payments'
    )

    track_id = models.BigIntegerField(
        verbose_name = 'کد پیگیری درگاه',
        unique = True,
        null = True,
        blank = True
    )

    amount = models.PositiveBigIntegerField(verbose_name = 'مبلغ (ریال)')

    status = models.CharField(
        verbose_name = 'وضعیت',
        choices = STATUS_CHOICE,
        default = PENDING,
        max_length = 10
    )

    gateway_status = models.IntegerField(verbose_name = 'وضعیت درگاه', null = True, blank = True)
    ref_number = models.CharField(verbose_name = 'شماره مرجع', max_length = 64, blank = True)
    card_number = models.CharField(verbose_name = 'کارت پرداخت‌کننده', max_length = 32, blank = True)
    paid_date = models.DateTimeField(verbose_name = 'زمان پرداخت', null = True, blank = True)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now = True)

    class Meta:
        verbose_name = 'پرداخت'
        verbose_name_plural = 'پرداخت ها'
        ordering = ('-created_date',)

    def __str__(self):
        return f'{self.order_id} - {self.get_status_display()}'