from django import forms
from .models import Order

class OrderModelForm(forms.ModelForm):

    """
    Checkout form that collects the delivery details of an order.

    Besides the ``Order`` fields (address, names, postal code) it has extra fields
    that are not stored on the order: ``state_select`` and ``city_select`` (merged
    into the address by ``clean``), ``terms`` (must always be accepted),
    ``confirm_info`` (required only on the review step) and the hidden flag
    ``is_review_submission``, which marks a submission from the review page.
    """

    state_select = forms.CharField(required=True)
    city_select = forms.CharField(required=True)
    terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'لطفاً قوانین و مقررات را بپذیرید.'}
    )
    confirm_info = forms.BooleanField(required=False)
    is_review_submission = forms.BooleanField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Order

        fields = [
            'address','first_name','last_name',
            'postal_code'
        ]

    def clean(self):

        """
        Merge state, city and street into one address and validate the review step.

        The state and city arrive in separate fields (``state_select`` and
        ``city_select``) and are joined with the street into an address of the form
        ``"<state>, <city>, <street>"``.

        The form is posted from two pages. A submission from ``OrderReview`` carries
        ``is_review_submission`` and then ``confirm_info`` must be ticked. A
        submission from ``OrderView`` (first fill or editing the details) does not
        carry the flag, so ``confirm_info`` is optional.

        Returns:
            The cleaned data with the merged ``address``.

        Note:
            If the submitted street already contains the state and city, they are
            repeated in the merged address.
        """
        
        cleaned_data = super().clean()
        state = cleaned_data.get('state_select')
        city = cleaned_data.get('city_select')
        address = cleaned_data.get('address')

        cleaned_data['address'] = ', '.join(part for part in (state, city, address) if part)

        if cleaned_data.get('is_review_submission') and not cleaned_data.get('confirm_info'):
            self.add_error('confirm_info', 'لطفاً صحت اطلاعات را تایید کنید.')

        return cleaned_data
    
