from django import forms
from .models import Favorites

class AddtoFavorites(forms.ModelForm):
    class Meta:

        model = Favorites
        fields = ['product_id']
        widgets = {
            'product_id': forms.HiddenInput(),
        }