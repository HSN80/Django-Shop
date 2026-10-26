from django.contrib import admin
from django import forms
from django.db.models import Count
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin
from .models import Catalog, Category, Discount, Comment, Image
from core.dashboard import LOW_STOCK
from .specs import SpecsField, build_suggestions

# Register your models here.

class StockFilter(admin.SimpleListFilter):
    
    """
    Sidebar filter that narrows products by stock level.

    Offers "out of stock" (stock is 0) and "low stock" (1 up to ``LOW_STOCK``).
    """

    title = 'موجودی'
    parameter_name = 'stock_state'

    def lookups(self, request, model_admin):

        """Return the filter choices shown in the sidebar."""

        return (('out', 'تمام‌شده'), ('low', f'کم‌موجود (۱ تا {LOW_STOCK})'))

    def queryset(self, request, queryset):

        """Apply the selected stock filter; with no selection, return the queryset unchanged."""

        if self.value() == 'out':
            return queryset.filter(stock=0)
        if self.value() == 'low':
            return queryset.filter(stock__range=(1, LOW_STOCK))
        return queryset

class CatalogAdminForm(forms.ModelForm):
    """Product form of the admin with the friendly specifications editor."""

    specs = SpecsField(label='مشخصات محصول')

    class Meta:
        model = Catalog
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['specs'].widget.suggestions = build_suggestions(exclude_pk=self.instance.pk)

@admin.register(Catalog)
class AdminCatalog(SimpleHistoryAdmin):

    """
    Admin for ``Catalog`` products with change history and stock tools.

    The list shows a thumbnail, price, discount, a stock-state label and the
    status, and supports searching by title, slug or category, and filtering by
    status, stock level, category and discount campaign. Status, stock and price
    can be edited straight from the list, and products can be published or moved
    to draft in bulk. The computed ``discount`` is read-only.

    Note:
        Edits made from the list go through ``Catalog.save``, which recalculates
        the discount, and are recorded in history.
    """

    form = CatalogAdminForm
    list_display = (
        'thumb', 'title', 'category', 'price', 'discount',
        'stock', 'stock_state', 'status', 'updated_date',
    )
    list_display_links = ('title',)
    list_filter = ('status', StockFilter, 'category', 'discount_campaign')
    search_fields = ('title', 'slug', 'category__title')
    list_editable = ('status', 'stock', 'price')
    list_select_related = ('category',)
    ordering = ('-id',)
    date_hierarchy = 'created_date'
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('discount',)
    filter_horizontal = ('images',)
    autocomplete_fields = ('category',)
    actions = ['publish', 'unpublish']

    fieldsets = (
        ('product description', {
            'fields': ('title', 'description', 'images', 'specs', 'slug', 'category'),
        }),
        ('pricing', {
            'fields': ('price', 'discount_campaign', 'discount'),
        }),
        ('out for sale', {
            'fields': ('status',),
        }),
    )

    def get_queryset(self, request):

        """Return the products with their images preloaded, for the thumbnail column."""

        return super().get_queryset(request).prefetch_related('images')

    @admin.display(description='')
    def thumb(self, obj):

        """Show the product's first image as a small thumbnail (a dash if none)."""
        
        images = list(obj.images.all())
        if images and images[0].image:
            return format_html(
                '<img src="{}" style="height:40px;border-radius:4px">',
                images[0].image.url,
            )
        return '—'

    @admin.display(description='وضعیت موجودی', ordering='stock')
    def stock_state(self, obj):

        """
        Show a coloured stock label: "out of stock", "low stock" or a check mark.

        "Low" means a stock of at most ``LOW_STOCK``. Sorting by this column sorts by
        the stock quantity.
        """

        if obj.stock == 0:
            return format_html('<b style="color:{}">{}</b>', '#c0392b', 'تمام شده')
        if obj.stock <= LOW_STOCK:
            return format_html('<b style="color:{}">{}</b>', '#e67e22', 'کم‌موجود')
        return '✓'

    def _set_status(self, request, queryset, status):

        """
        Set the status of every selected product (bulk-action helper).

        Args:
            request: The current admin request.
            queryset: The selected products.
            status: The new status, a ``Catalog.Status`` value.
        
        Note:
            Products already in that status are skipped. Each change is saved with a
            change reason so it appears in history.
        """

        changed = 0
        for product in queryset:
            if product.status != status:
                product.status = status
                product._change_reason = 'تغییر وضعیت از لیست ادمین'
                product.save(update_fields=['status', 'updated_date'])
                changed += 1
        self.message_user(request, f'{changed} محصول تغییر کرد.')

    @admin.action(description='انتشار محصولات انتخاب‌شده')
    def publish(self, request, queryset):

        """Publish the selected products."""

        self._set_status(request, queryset, Catalog.Status.PUBLISHED)

    @admin.action(description='تبدیل به پیش‌نویس')
    def unpublish(self, request, queryset):

        """Move the selected products back to draft."""

        self._set_status(request, queryset, Catalog.Status.DRAFT)


@admin.register(Category)
class AdminCategory(SimpleHistoryAdmin):

    """
    Admin for ``Category`` with change history and a product count.

    The slug is filled in from the title.
    """

    list_display = ('title', 'parent', 'products_count')
    search_fields = ('title', 'slug')
    list_select_related = ('parent',)
    prepopulated_fields = {'slug': ('title',)}

    def get_queryset(self, request):
       
        """
        Return categories annotated with ``products_count``.

        Note:
            The count uses ``'category'``, which is the ``related_name`` of
            ``Catalog.category`` (the reverse relation from a category to its
            products).
        """

        return super().get_queryset(request).annotate(products_count=Count('category'))

    @admin.display(description='تعداد محصول', ordering='products_count')
    def products_count(self, obj):

        """Show the number of products in the category, from the annotation."""

        return obj.products_count


@admin.register(Discount)
class AdminDiscount(SimpleHistoryAdmin):

    """
    Admin for ``Discount`` campaigns with change history.

    The active flag can be toggled from the list, and the list shows how many
    products each campaign applies to.

    Note:
        Saving a discount updates the computed discount of its products, so each
        affected product also gets a history record.
    """

    list_display = ('title', 'percent', 'is_active', 'products_count')
    list_editable = ('is_active',)
    list_filter = ('is_active',)

    def get_queryset(self, request):
        
        """Return discounts annotated with ``products_count``."""

        return super().get_queryset(request).annotate(products_count=Count('products'))

    @admin.display(description='تعداد محصول', ordering='products_count')
    def products_count(self, obj):
        
        """Show the number of products in the campaign, from the annotation."""

        return obj.products_count


@admin.register(Comment)
class AdminComment(SimpleHistoryAdmin):

    """
    Admin for moderating ``Comment`` objects.

    Comments can be filtered by status and date, searched by text, author or
    product, and approved or rejected in bulk. Relations use raw-id inputs so the
    form stays fast with many users and products.
    """

    list_display = ('short_body', 'user', 'product', 'status', 'is_reply', 'created_date')
    list_filter = ('status', 'created_date')
    search_fields = ('body', 'user__user__username', 'product__title')
    list_select_related = ('user__user', 'product', 'parent')
    raw_id_fields = ('user', 'product', 'parent')
    actions = ['approve', 'reject']

    @admin.display(description='متن')
    def short_body(self, obj):

        """Show the first 50 characters of the comment."""

        return obj.body[:50]

    @admin.display(boolean=True, description='پاسخ؟')
    def is_reply(self, obj):

        """Show whether the comment is a reply to another comment."""

        return obj.parent_id is not None

    def _set_status(self, request, queryset, status):

        """
        Set the status of every selected comment (bulk-action helper).

        Args:
            request: The current admin request.
            queryset: The selected comments.
            status: The new status (``approved`` or ``rejected``).

        Note:
            Comments already in that status are skipped. Each change is saved with a
            change reason so it appears in history.
        """

        changed = 0
        for comment in queryset:
            if comment.status != status:
                comment.status = status
                comment._change_reason = 'تغییر وضعیت از لیست ادمین'
                comment.save(update_fields=['status', 'updated_date'])
                changed += 1
        self.message_user(request, f'{changed} نظر تغییر کرد.')

    @admin.action(description='تأیید نظرات انتخاب‌شده')
    def approve(self, request, queryset):
        
        """Approve the selected comments."""

        self._set_status(request, queryset, 'approved')

    @admin.action(description='رد نظرات انتخاب‌شده')
    def reject(self, request, queryset):
        
        """Reject the selected comments."""

        self._set_status(request, queryset, 'rejected')


@admin.register(Image)
class AdminImage(SimpleHistoryAdmin):
    
    """Admin for ``Image`` with change history and a thumbnail preview."""

    list_display = ('preview', 'created_date')

    @admin.display(description='تصویر')
    def preview(self, obj):
        
        """Show a small preview of the image (a dash if the file is missing)."""

        if obj.image:
            return format_html('<img src="{}" style="height:50px">', obj.image.url)
        return '—'