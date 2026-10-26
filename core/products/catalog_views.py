from django.db.models import Prefetch
from django.views.generic import ListView, DetailView
from .models import Catalog, Comment


"""
Views for the products app: the public product list and detail pages, and
the staff views that create, edit and delete products.
"""


class CatalogListView(ListView):

    """
    Home page: list the published products.

    Attributes:
        template_name: Template used for the home page.
        context_object_name: The products are available as ``products``.
    """

    template_name = 'index.html' #'products/catalog/catalog_list.html'
    context_object_name = 'products'
    def get_queryset(self):

        """Return the published products, with their categories fetched in one query."""

        return Catalog.published.select_related('category')


class CatalogDetailView(DetailView):

    """
    Show one published product, found by its slug, with its approved comments.

    Attributes:
        template_name: Template that renders the product page.
        slug_field: Model field matched against the URL.
        slug_url_kwarg: Name of the URL keyword that carries the slug.
        context_object_name: The product is available as ``product``.
    """

    template_name = 'products/catalog/product-details.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    context_object_name = 'product'

    def get_queryset(self):

        """
        Return the published products with their related data preloaded.

        Loads each product's category and discount campaign, and its approved
        comments together with the approved replies of each comment, so the page does
        not run extra queries per comment.

        Note:
            Only published products are reachable, so a draft product returns 404
            even for staff.
        """

        replies = Comment.objects.filter(status='approved').select_related('user')
        comments = Comment.objects.filter(
            status = 'approved').select_related('user').prefetch_related(
                Prefetch('replies', queryset = replies)
            )

        return Catalog.published.select_related(
            'category','discount_campaign',).prefetch_related(
                Prefetch('comments', queryset = comments)
                )
    
    def get_context_data(self, **kwargs):

        """
        Add detail-page data and remember the viewed product.

        Stores the product's primary key in the session under ``'product'``. If the
        product has a discount, adds ``save_price`` (the amount the buyer saves) to
        the context.

        Returns:
            The template context.

        Note:
            The session entry is overwritten on every visit, so it always refers to
            the product the user viewed last.
        """

        context = super().get_context_data(**kwargs)
        product = self.object
        self.request.session['product'] = product.pk
        if product.discount:
            context['save_price'] = product.price - product.discount
        return context

