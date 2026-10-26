from django.db import models
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords
from .managers import CartManager


# Create your models here.

class Cart(models.Model):

    """
    A user's shopping cart.

    Attributes:
        STATUS_CHOICE: Available statuses: ``empty``, ``updating``, ``active``,
            ``abandoned`` and ``checkout``.
        profile: The owner; deleting the profile deletes the cart.
        status: Current status, ``empty`` by default.
        created_date: When the cart was created.
        updated_date: When the cart was last saved.

    Note:
        A database constraint allows only one ``active`` cart per profile; any
        number of carts in other statuses is allowed. Checkout moves the cart to
        ``updating`` (see ``OrderView.form_valid``), which frees the owner to
        start a new active cart.
    """

    STATUS_CHOICE = (
        ('empty', 'خالی'),
        ('updating', 'بروزرسانی'),
        ('active', 'فعال'),
        ('abandoned', 'رها شده'),
        ('checkout', 'پرداخت')
    )

    profile = models.ForeignKey(
        'accounts.Profile',
        verbose_name = 'کاربر',
        on_delete = models.CASCADE,
        related_name = 'carts'
    )

    status = models.CharField(
        verbose_name = 'وضعیت',
        choices = STATUS_CHOICE,
        default = 'empty',
        max_length = 10
    )
    
    objects = CartManager()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now = True)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.profile.user} - {self.status}'
    
    @property
    def items_count(self):

        """
        Return the total number of units in the cart (sum of item quantities).

        Note:
            Reads ``cart_items`` on every access; use ``prefetch_related`` when
            evaluating many carts to avoid extra queries.
        """

        return sum(item.quantity for item in self.cart_items.all())
    
    @property
    def total_price(self):

        """
        Return the cart total at the products' *current* final prices.

        Each item contributes ``product.final_price * quantity``, so a later price
        change or discount changes the total.

        Note:
            This does not use the price stored on ``CartItem.price``. Reads the
            items and their products on every access; prefetch both when evaluating
            many carts.
        """

        return sum(item.product.final_price * item.quantity for item in self.cart_items.all())

    class Meta:
        verbose_name = 'سبد خرید'
        verbose_name_plural = 'سبدها'
        ordering = ('created_date',)

        constraints = [
            models.UniqueConstraint(
                fields = ['profile','status'],
                condition = models.Q(status='active'),
                name = 'unique_active_cart'
            )
        ]



class CartItem(models.Model):

    """
    One product line in a cart.

    Attributes:
        cart: The cart this line belongs to; deleting the cart deletes the line.
        product: The product in the line; deleting the product removes the line.
        quantity: Number of units, ``0`` by default.
        price: The product's final price recorded when the line was first saved
            (optional).
        created_date: When the line was created.
        updated_date: When the line was last saved.
    """

    cart = models.ForeignKey(
        'carts.Cart',
        verbose_name = 'سبد',
        on_delete = models.CASCADE,
        related_name = 'cart_items'
    )

    product = models.ForeignKey(
        'products.Catalog',
        verbose_name = 'محصولات',
        on_delete = models.CASCADE,
        related_name = 'cart_items'
    )

    quantity = models.PositiveIntegerField(
        verbose_name = 'تعداد',
        default = 0
    )

    price = models.DecimalField(
        verbose_name = 'قیمت محصول',
        decimal_places = 0,
        max_digits = 13,
        null = True,
        blank = True
    )

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now = True)

    def __str__(self):
        return f'{self.cart} : {self.product} - {self.quantity}'
    
    class Meta:
        verbose_name = 'محصول سبد'
        verbose_name_plural = 'محصولات سبد'
        ordering = ('created_date',)

    def clean(self):

        """
        Check that the line can be satisfied from the current stock.

        Raises:
            ValidationError: If ``quantity`` is higher than the product's stock
                (attached to ``quantity``), or if the stock is zero (attached to
                ``product``).

        Note:
            Nothing is checked until both a product and a quantity are set. For a
            product with zero stock and a positive quantity, the quantity error is
            raised first, so the "not in stock" message only appears when the
            quantity is zero.
        """

        super().clean()
    
        if not self.product or self.quantity is None:
            return
        
        stock = self.product.stock

        if self.quantity > stock:
            raise ValidationError({
                'quantity': f'تعداد درخواستی ({self.quantity}) بیشتر از موجودی انبار ({stock}) میباشد.'
            })
        
        if stock == 0:
            raise ValidationError({
                'product': 'این محصول در انبار موجود نیست.'
            })
        
    def save(self, *args, **kwargs):

        """
        Save the line, filling in the price and validating it first.

        If ``price`` is empty, it is set to the product's current ``final_price``.
        ``full_clean`` then runs, so the stock check applies on every save.

        Args:
            *args: Passed to ``Model.save``.
            **kwargs: Passed to ``Model.save``.

        Returns:
            The result of ``Model.save``.

        Raises:
            ValidationError: If validation fails, for example when the quantity
                exceeds the stock.

        Note:
            Because validation runs on every save, an existing line cannot be saved
            again once the stock has dropped below its quantity. A price of ``0`` is
            treated as empty and gets replaced.
        """

        if not self.price and self.product:
            self.price = self.product.final_price
            
        self.full_clean()
        return super().save(*args,**kwargs)
    
