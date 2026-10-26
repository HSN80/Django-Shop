from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import FormView, DeleteView
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from .models import Cart, CartItem
from . forms import AddToCartForm
from products.models import Catalog

# Create your views here.

class AddToCartView(LoginRequiredMixin,FormView):

    '''
    adding products to existing active cart.
    '''

    form_class = AddToCartForm

    def get_success_url(self):
        '''getting product id from session and returning user to its product page.'''
        product = self.request.session.get('product')
        product_obj = get_object_or_404(Catalog, pk = product)
        return product_obj.get_absolute_url()


    def form_valid(self, form):

        '''
        creating new cart object or if there is any active one,
        checks for its item, if select items already exists in
        cart, updating its quantity and if its not exists, add
        them in.
        also if demanding quantity of the specefic item is more than
        Catalog.stock field , returning validation error insted of saving.
        '''
        
        product = form.cleaned_data['product']
        quantity = form.cleaned_data['quantity']
        profile = self.request.user.profile

        cart = Cart.objects.filter(
            profile=profile,
            status__in=['empty','active']
        ).first()
        
        if not cart:
            cart= Cart.objects.create(
                profile=profile,
                status='active',
            )

        if cart.status == 'empty':
            cart.status = 'active'
            cart.save(update_fields=['status'])

        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not item_created:
            cart_item.quantity += quantity

        try:
            cart_item.save()
            messages.success(self.request, f'محصول "{product}" به سبد خرید اضافه شد.')
        except ValidationError as e:
            for error in e.messages:
                messages.error(self.request, error)
            return redirect(self.request.META.get('HTTP_REFERER', 'products:Catalog_detail'))

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'اطلاعات ارسالی معتبر نیست.')
        return redirect(self.request.META.get('HTTP_REFERER', 'products:product_list'))

class DeleteFromCartView(LoginRequiredMixin,DeleteView):
    '''deleting items from a active cart.'''
    model = CartItem
    
    def post(self, request, *args, **kwargs):

        self.object = self.get_object()
        cart = self.object.cart
        if cart.profile != self.request.user.profile:
            raise Http404()
        
        respone = super().post(request, *args, **kwargs)

        if not cart.cart_items.exists():
            cart.status = 'empty'
            cart.save(update_fields=['status'])

        return respone
        
    def get_success_url(self):
        
        product = self.request.session.get('product')
        product_obj = get_object_or_404(Catalog, pk = product)
        return product_obj.get_absolute_url()

class CancelCartView(LoginRequiredMixin,View):
    
    def get(self, request, pk):

        cart = get_object_or_404(Cart, pk=pk )
        profile = self.request.user.profile

        if cart.profile == profile and cart.status in ['active', 'updating']:

            cart.status = 'abandoned'
            cart.save(update_fields=['status'])
            return redirect('accounts:Profile')
        
        else:
            raise Http404()
        