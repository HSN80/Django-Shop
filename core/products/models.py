from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from simple_history.models import HistoricalRecords
from . import managers

# Create your models here.

User = get_user_model()

class Catalog(models.Model):
    
    """
    A product that can be sold in the shop.

    Attributes:
        Status: Publication states: ``DRAFT`` (``'DF'``) and ``PUBLISHED``
            (``'PB'``).
        title: Unique product name.
        description: Long description.
        images: Product pictures (many-to-many with ``Image``).
        slug: Unique URL slug; Unicode is allowed.
        specs: Free-form specifications stored as JSON.
        stock: Units in stock, 1 by default.
        price: Regular price in Toman.
        discount: The price *after* the discount (not the discount amount);
            ``None`` when no active campaign applies. Calculated by ``save``.
        discount_campaign: The campaign applied to this product (optional).
            Deleting the campaign clears this link.
        category: The product's category. Protected: a category that still has
            products cannot be deleted.
        status: Publication status, ``DRAFT`` by default.
        created_date: When the product was created.
        updated_date: When the product was last saved.
        objects: Manager returning every product, drafts included.
        published: Manager returning only published products.

    Note:
        ``objects`` is the default manager, so the admin lists drafts too, while
        public pages use ``published``. Products are ordered newest first. From a
        ``Category`` the products are reached through the reverse name
        ``category``, which is the ``related_name`` of the ``category`` field.
    """

    class Status(models.TextChoices):
        DRAFT = 'DF', 'پیش نویس'
        PUBLISHED = 'PB', 'منتشر شده'

    title = models.CharField(verbose_name='نام محصول.', max_length=128,unique=True,)
    description = models.TextField(verbose_name='توضیحات محصول')
    images = models.ManyToManyField(
        'Image',
        related_name = 'product',
        verbose_name='تصاویر',
    )
    slug = models.SlugField(verbose_name='slug', max_length=255, unique=True, db_index=True, allow_unicode=True)
    specs = models.JSONField(verbose_name='مشخصات محصول', default=dict, blank=True, null=True,)
    stock = models.PositiveIntegerField(verbose_name='تعداد در انبار', default=1)
    price = models.DecimalField(verbose_name='قیمت محصول', max_digits=13, decimal_places=0,)
    discount = models.DecimalField(verbose_name='قیمت پس از تخفیف', max_digits=13, decimal_places=0, null=True, blank=True)
    discount_campaign = models.ForeignKey(
        'Discount',
        on_delete= models.SET_NULL,
        null=True,
        blank=True,
        related_name= 'products',
        verbose_name= 'کمپین تخفیف'
    )
        
    def snippet(self):
        
        """Return the first 25 characters of the description followed by ``'...'``."""

        return self.description[:25] + '...'


    category = models.ForeignKey('Category', verbose_name='دسته بندی', related_name='category', on_delete=models.PROTECT)
    status = models.CharField(verbose_name='وضعیت محصول', max_length=2, choices=Status.choices, default=Status.DRAFT)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    published = managers.PublishedManager()
    history = HistoricalRecords()

    class Meta:

        ordering = ['-created_date']
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'

    @property
    def final_price(self):
        
        """
        Return the price a customer pays: the discounted price if there is one,
        otherwise the regular price.

        Note:
            A discounted price of 0 is treated as "no discount".
        """

        value = 0
        if self.discount:
            value = self.discount
        else:
            value = self.price
        return value


    def __str__(self):
        
        """Return the product title."""
        
        return self.title
    
    def get_absolute_url(self):
        
        """
        Return the URL of the product's detail page.

        The URL contains the product's slug and the full path of its category
        (``'<root>/<child>/...'``).

        Returns:
            The URL for the ``products:Catalog_detail`` route.
        """

        if self.category:
            category_path = self.category.get_category_path()
        else:
            category_path = 'uncategorized'

        return reverse('products:Catalog_detail',
                        kwargs={'slug': self.slug, 'category_path':category_path})
    
    def save(self, *args, **kwargs):

        """
        Save the product, recalculating its discounted price first.

        If the product has an active discount campaign, ``discount`` is set to
        ``price`` minus the campaign percentage; otherwise it is cleared.

        Args:
            *args: Passed to ``Model.save``.
            **kwargs: Passed to ``Model.save``.

        Note:
            The calculation runs on every save, so a value typed into ``discount`` is
            always overwritten. When ``update_fields`` is used without ``'discount'``
            the recalculated value is not written to the database.
        """

        if self.discount_campaign and self.discount_campaign.is_active:
            discount_amount = (self.price * self.discount_campaign.percent) / 100
            self.discount = self.price - discount_amount
        else:
            self.discount = None

        super().save(*args, **kwargs)
        
    
class Category(models.Model):

    """
    A node in the product category tree.

    Attributes:
        title: Category name.
        slug: Unique slug, generated from the title on every save.
        parent: The parent category, or ``None`` for a top-level category;
            deleting a parent deletes its children.

    Note:
        Because the slug is derived from the title, renaming a category changes
        its slug and therefore the URLs of its products, and two categories with
        the same title cannot exist. A category that has products cannot be
        deleted (products protect their category).
    """

    title = models.CharField(verbose_name='نام دسته بندی', max_length=255)
    slug = models.SlugField(verbose_name='اسلاگ', max_length=255, unique=True, allow_unicode=True,)

    parent = models.ForeignKey(
        'self',
        verbose_name='کلاس مادر',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    history = HistoricalRecords()

    def get_category_path(self):

        """
        Return the slugs from the top-level ancestor down to this category.

        Returns:
            A string such as ``'electronics/phones/android'``; for a top-level
            category it is just its own slug.
        """

        path = [self.slug]
        parent_obj = self.parent
        
        while parent_obj is not None:
            path.append(parent_obj.slug)
            parent_obj = parent_obj.parent
        return '/'.join(reversed(path))
        
    class Meta:

        verbose_name = 'دسته بندی'
        verbose_name_plural = 'دسته بندی ها'

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):

        """
        Save the category after regenerating its slug from the title.

        Args:
            *args: Passed to ``Model.save``.
            **kwargs: Passed to ``Model.save``.

        Returns:
            The result of ``Model.save``.
        """

        self.slug = slugify(self.title, allow_unicode=True)
        return super().save(*args, **kwargs)


class Discount(models.Model):

    """
    A discount campaign that can be attached to many products.

    Attributes:
        title: Campaign name.
        percent: Discount percentage, from 1 to 100.
        is_active: Whether the campaign currently applies. An inactive campaign
            gives no discount.
        products: Reverse relation to the products using this campaign.
    """

    title = models.CharField(verbose_name='عنوان تخفیف', max_length=255)
    percent = models.PositiveIntegerField(verbose_name='درصد تخفیف', validators=[MinValueValidator(1), MaxValueValidator(100)])
    
    is_active = models.BooleanField(default=True)
    history = HistoricalRecords()

    class Meta:

        verbose_name = 'تخفیف'
        verbose_name_plural = 'تخفیفات'

    def __str__(self):
        
        """Return the title with the percentage, e.g. ``'Summer sale (20%)'``."""

        return f'{self.title} ({self.percent}%)'
    
    def save(self, *args, **kwargs):

        """
        Save the campaign and re-save every product that uses it.

        Re-saving the products recalculates their discounted prices, so a changed
        percentage or active flag takes effect immediately.

        Args:
            *args: Passed to ``Model.save``.
            **kwargs: Passed to ``Model.save``.
        """

        super().save(*args, **kwargs)

        for product in self.products.all():
            product.save()

class Comment(models.Model):

    """
    A comment on a product, or a reply to another comment.

    Attributes:
        STATUS_CHOICES: Moderation states: ``pending``, ``approved`` and
            ``rejected``.
        user: The profile that wrote the comment.
        product: The commented product (optional); deleting the product deletes
            its comments.
        parent: The comment this one replies to, or ``None`` for a top-level
            comment (reverse name ``replies``); deleting a comment deletes its
            replies.
        body: The comment text.
        status: Moderation status, ``pending`` by default.
        created_date: When the comment was written.
        updated_date: When the comment was last saved.

    Note:
        Comments are ordered by creation date, oldest first. Only approved
        comments are shown on product pages.
    """

    STATUS_CHOICES = (
        ('pending', 'در انتظار'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده')
    )

    user = models.ForeignKey(
        'accounts.Profile',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='کاربر')
    
    product = models.ForeignKey(
        Catalog,on_delete=models.CASCADE,
        null = True,
        blank = True,
        related_name='comments',verbose_name='محصول')

    parent = models.ForeignKey(
        'self',on_delete=models.CASCADE,null=True,blank=True,
        related_name='replies',verbose_name='پاسخ')
    
    body = models.TextField(verbose_name='متن نظر')

    status = models.CharField(
        verbose_name='وضعیت',max_length=10,choices=STATUS_CHOICES, default='pending')

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'
        ordering = ('created_date',)

    def __str__(self):
        return f'{self.user} - {self.get_status_display()}'
    
    @property
    def is_reply(self):

        """Return ``True`` if this comment is a reply to another comment."""

        return self.parent is not None

class Image(models.Model):

    """
    A product picture, stored under ``products/`` in the media folder.

    Attributes:
        image: The image file (optional).
        created_date: When the image was uploaded.
        updated_date: When the record was last saved.
    
    Note:
        Images are ordered newest first. One image can be shared by several
        products through ``Catalog.images``.
    """

    image = models.ImageField(verbose_name='تصویر',upload_to='products/',null=True,blank=True)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    
    class Meta:

        ordering = ['-created_date']
        verbose_name = 'تصویر'
        verbose_name_plural = 'تصاویر'

    def __str__(self):
        
        return f'تصویر {self.pk}'
