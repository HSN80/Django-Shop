from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import CreateView, DeleteView
from .models import Comment, Catalog
from django.contrib.auth.mixins import LoginRequiredMixin

# Create your views here.

"""
Views for creating and deleting product comments.

Both views are form endpoints used from the product page; they have no page
of their own and redirect back after the action.
"""

class CommentCreateView(LoginRequiredMixin,CreateView):

    """
    Add a comment, or a reply to a comment, on the product the user is viewing.

    Requires login. The product is the one stored in the session by
    ``CatalogDetailView`` (the product viewed last), and the comment is saved on
    the current user's profile.

    Attributes:
        model: The ``Comment`` model.
        fields: The submitted fields: the text and, for a reply, the parent
            comment.

    Note:
        A reply must belong to the same product as the new comment. If no product
        is stored in the session (for example the session expired), the user is
        sent back to the catalog with an error. New comments may need approval
        before they are shown.
    """

    model = Comment
    fields = ['body','parent']

    def dispatch(self, request, *args, **kwargs):

        """
        Find the product to comment on before handling the request.

        Anonymous users skip this step and are sent to the login page by the parent
        class. A logged-in user without a valid published product in the session is
        redirected to the catalog with an error message.
        """

        if request.user.is_authenticated:
            product_id = request.session.get('product')
            self.product = Catalog.published.filter(pk=product_id).first() if product_id else None
            if self.product is None:
                messages.error(request, 'محصولی برای ثبت نظر انتخاب نشده است.')
                return redirect('products:Catalog_list')
        return super().dispatch(request, *args, **kwargs)

    
    def get_success_url(self):

        """Return the URL of the product page, so the user lands back on it."""
        
        product = self.request.session.get('product')
        product_obj = get_object_or_404(Catalog, pk = product)
        return product_obj.get_absolute_url()
    
    def form_valid(self, form):
        
        """
        Save the comment on the current product and the user's profile.

        A reply whose parent belongs to another product is rejected as a form error.

        Returns:
            A redirect to the product page, with a confirmation message.
        """

        parent = form.cleaned_data.get('parent')
        if parent and parent.product_id != self.product.pk:
            form.add_error('parent', 'این نظر متعلق به محصول دیگری است.')
            return self.form_invalid(form)

        form.instance.user = self.request.user.profile
        form.instance.product = self.product
        messages.success(self.request, 'نظر شما ثبت شد و پس از تأیید نمایش داده می‌شود.')
        return super().form_valid(form)

    def form_invalid(self, form):

        """
        Report validation errors as messages and redirect back to the product page.

        The form is not shown again, so the user's text is lost.
        """

        for errors in form.errors.values():
            for error in errors:
                messages.error(self.request, error)
        return redirect(self.get_success_url())

class CommentDelete(LoginRequiredMixin,DeleteView):

    """
    Delete a comment (POST only).

    Requires login. Users can delete only their own comments; staff can delete
    any comment. Other ids return 404. After deleting, the user is redirected to
    the page they came from.
    """

    model = Comment
    http_method_names = ['post']

    def get_queryset(self):
        
        """Limit deletable comments to the user's own, or all of them for staff."""

        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(user=self.request.user.profile)

    def get_success_url(self):

        """Return the page the user came from (``Referer``), or ``'/'`` if unknown."""

        return self.request.META.get('HTTP_REFERER') or '/'

    def form_valid(self, form):
        
        """Delete the comment, then queue a success message."""

        response = super().form_valid(form)
        messages.success(self.request, 'نظر با موفقیت پاک شد.')
        return response