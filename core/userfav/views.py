from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import DeleteView, FormView
from django.contrib import messages
from .models import Favorites
from .froms import AddtoFavorites

# Create your views here.

"""
Views for the userfav app: add a product to the current user's favorites,
remove one, and list them.

All views require login and only touch the current user's own favorites.
"""

class FavoriteCreate(LoginRequiredMixin,FormView):

    """
    Add a product to the current user's favorites.

    Handles the POST of ``AddtoFavorites`` (a product id) and redirects back to
    the page the user came from. Adding a product that is already a favorite does
    nothing.

    Attributes:
        form_class: The form that validates the submitted product id.
        success_url: Fallback redirect target when the request has no
            ``Referer`` header.

    Note:
        The view has no template, so it accepts POST only.
    """

    form_class = AddtoFavorites
    success_url = reverse_lazy('products:Catalog_detail')
    http_method_names = ['post']

    def form_valid(self, form):

        """
        Create the favorite for the current user and redirect back.

        Uses ``get_or_create``, so submitting the same product twice never creates a
        duplicate. A success message is shown only when a new favorite was created.

        Returns:
            A redirect to the ``Referer`` URL, or to ``success_url`` if it is missing.
        """

        product = form.cleaned_data['product_id']
        profile = self.request.user.profile
        
        fav_item, created = Favorites.objects.get_or_create(
            product_id = product,
            profile = profile
        )
        
        if created:
            messages.success(self.request, f'محصول {product} با موفقیت به علاقه مندی ها اضافه شد.')
        
        return redirect(self.request.META.get('HTTP_REFERER', self.success_url))
    
    def form_invalid(self, form):

        """
        Show an error message and redirect back to the previous page.

        Returns:
            A redirect to the ``Referer`` URL, or to the catalog list if it is
            missing.
        """

        messages.error(self.request, 'اطلاعات ارسالی معتبر نیست.')
        return redirect(self.request.META.get('HTTP_REFERER', 'products:product_list'))

class FavoriteDelete(DeleteView):

    """
    Delete one of the current user's favorites.

    Only favorites owned by the current user can be deleted; any other id returns
    404. A GET request shows the confirmation page, a POST deletes the favorite.
    """

    model = Favorites

    def get_queryset(self):
        
        """Limit deletable favorites to those owned by the current user."""

        return super().get_queryset().filter(profile=self.request.user.profile)
    
    def get_success_url(self):
        
        """Return the page the user came from (``Referer``), or ``'/'`` if unknown."""

        refer = self.request.META.get('HTTP_REFERER')
        return refer or '/'

