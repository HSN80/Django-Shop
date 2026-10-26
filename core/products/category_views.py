from django.shortcuts import get_object_or_404
from django.db.models import Max, Min
from django.views.generic import ListView
from .models import Category, Catalog

"""
Views for browsing, creating and deleting product categories.

The main view is ``CategoryListView``, the public category page with price,
ordering and page-size filters.
"""


class CategoryListView(ListView):

    """
    Category page: the products of one category, with filters and paging.

    The category is taken from the ``category_path`` URL keyword (only the last
    slug is used). The page understands these query parameters:

    * ``ordering_by``: ``low_to_high``, ``high_to_low`` or ``newest``.
    * ``min_price`` and ``max_price``: the price range, kept within the cheapest
      and the most expensive product of the category.
    * ``per_page``: one of ``allowed_page_size`` (12 by default).
    * ``page``: the page number.

    Attributes:
        model: The ``Catalog`` model; the list shows products, not categories.
        template_name: Template that renders the category page.
        context_object_name: The products are available as ``products``.
        paginate_by: Default number of products per page.
        allowed_page_size: Page sizes the user may choose from.
        ordering_map: Maps an ``ordering_by`` value to a model ordering.
        ordering_labels: Maps an ``ordering_by`` value to its display label.

    Note:
        Only published products are listed, and the list is empty when the URL
        has no category. Invalid parameter values are ignored and replaced with
        the defaults. The category is found by its last slug only, so the parent
        segments of the path are not checked.
    """
    
    model = Catalog
    template_name = 'products/category/category.html'
    context_object_name = 'products'
    paginate_by = 12

    allowed_page_size = [12 ,24, 48, 96]
    ordering_map = {
        'high_to_low': '-price',
        'low_to_high': 'price',
        'newest': '-created_date'
    }

    ordering_labels = {
        'low_to_high': 'ارزان‌ترین',
        'high_to_low': 'گران‌ترین',
        'newest': 'جدیدترین',
    }

    def get_active_filters(self):

        """
        Return the filters currently applied, for the "active filters" chips.

        Covers the ordering, a price range narrower than the full range of the
        category, and a page size other than the default.

        Returns:
            A list of dicts with ``label`` and ``remove_url``, where ``remove_url``
            is the current query string without that filter and without ``page``.
        """

        filters = []
        ordering_by = self.request.GET.get('ordering_by')
        if ordering_by in self.ordering_map:
            params = self.request.GET.copy()
            params.pop('ordering_by', None)
            params.pop('page', None)
            filters.append({'label': self.ordering_labels[ordering_by], 'remove_url': '?' + params.urlencode()})

        pb = self.get_price_bounds()
        if pb['min_price'] != pb['absolute_min'] or pb['max_price'] != pb['absolute_max']:
            params = self.request.GET.copy()
            params.pop('min_price', None)
            params.pop('max_price', None)
            params.pop('page', None)
            label = f"{pb['min_price']:,} تا {pb['max_price']:,} تومان"
            filters.append({'label': label, 'remove_url': '?' + params.urlencode()})

        per_page = self.get_paginate_by(None)
        if per_page != self.paginate_by:
            params = self.request.GET.copy()
            params.pop('per_page', None)
            params.pop('page', None)
            filters.append({'label': f'{per_page} مورد در صفحه', 'remove_url': '?' + params.urlencode()})

        return filters
    
    def get_price_bounds(self):

        """
        Return the price range of the category and the range chosen by the user.

        Returns:
            A dict with ``absolute_min`` and ``absolute_max`` (the cheapest and most
            expensive published product in the category, or 0 if there are none) and
            ``min_price`` and ``max_price`` (the chosen range). The chosen values
            default to the absolute ones, are kept within them and are swapped if
            given in reverse order.

        Note:
            The result is cached on the view, so it is computed once per request.
        """

        if hasattr(self, '_price_bounds'):
            return self._price_bounds

        category = self.get_selected_category()
        if category is not None:
            agg = Catalog.published.filter(category=category).aggregate(
                min_price=Min('price'), max_price=Max('price')
            )
        else:
            agg = {'min_price': None, 'max_price': None}

        absolute_min = agg['min_price'] or 0
        absolute_max = agg['max_price'] or absolute_min or 0

        def parse(value, fallback):
            try:
                return int(value)
            except (TypeError, ValueError):
                return fallback

        min_price = parse(self.request.GET.get('min_price'), absolute_min)
        max_price = parse(self.request.GET.get('max_price'), absolute_max)
        min_price = max(absolute_min, min(min_price, absolute_max))
        max_price = max(absolute_min, min(max_price, absolute_max))
        if min_price > max_price:
            min_price, max_price = max_price, min_price

        self._price_bounds = {
            'absolute_min': absolute_min,
            'absolute_max': absolute_max,
            'min_price': min_price,
            'max_price': max_price,
        }
        return self._price_bounds

    def get_ordering(self):

        """Return the model ordering for ``ordering_by``, or ``None`` if it is missing or invalid."""
        
        return self.ordering_map.get(self.request.GET.get('ordering_by'))
    
    def get_paginate_by(self, queryset):

        """
        Return the page size from ``per_page`` if it is allowed, else the default.

        Args:
            queryset: Unused; passed by Django.
        """

        try:
            per_page = int(self.request.GET.get('per_page', self.paginate_by))
        except (TypeError, ValueError):
            return self.paginate_by
        if per_page not in self.allowed_page_size:
            return self.paginate_by
        return per_page

    def get_selected_category(self):

        """
        Return the category named in the URL, or ``None`` if there is no ``category_path``.

        Raises:
            Http404: If no category has the last slug of the path.
        """

        category_path = self.kwargs.get('category_path')
        if not category_path:
            return None
        leaf_slug = category_path.rstrip('/').split('/')[-1]
        return get_object_or_404(Category, slug=leaf_slug)

    def get_queryset(self):

        """
        Return the published products of the selected category in the chosen price range.

        The requested ordering is applied, with the newest first as a tie-breaker.
        Without a selected category an empty queryset is returned.
        """

        category = self.get_selected_category()

        if category is None:
            return Catalog.published.none()
        
        queryset = Catalog.published.filter(category=category)
        ordering = self.get_ordering()

        price_bounds = self.get_price_bounds()
        queryset = queryset.filter(
            price__gte=price_bounds['min_price'],
            price__lte=price_bounds['max_price'],
        )

        if ordering:
            queryset = queryset.order_by(ordering, '-created_date')

        return queryset
        

    def get_context_data(self, **kwargs):

        """
        Add everything the category template needs.

        Adds ``categories`` (top-level categories with their children),
        ``selected_category``, ``ordering_by``, ``query_string`` (the current filters
        without the page number, for building page links), ``per_page``,
        ``price_bounds`` and ``active_filters``. For paginated results it also adds
        ``page_ellipsis`` and ``elided_page_range`` for a compact page selector.
        """

        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(parent__isnull=True).prefetch_related('children')
        context['selected_category'] = self.get_selected_category()
        context['ordering_by'] = self.request.GET.get('ordering_by', '')
        
        params = self.request.GET.copy()
        params.pop('page', None)

        context['query_string'] = params.urlencode()

        context['per_page'] = self.get_paginate_by(None)
        context['price_bounds'] = self.get_price_bounds()
        context['active_filters'] = self.get_active_filters()

        if context.get('is_paginated'):
            paginator = context['paginator']
            context['page_ellipsis'] = paginator.ELLIPSIS
            context['elided_page_range'] = paginator.get_elided_page_range(
                context['page_obj'].number, on_each_side=1, on_ends=1
            )

        return context
    
