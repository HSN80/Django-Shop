from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Profile
from django.contrib.auth import get_user_model

user = get_user_model()

class ProfileModelForm(forms.ModelForm):

    """
    Form for editing a user's profile.

    Besides the model fields it requires a state and a city (``state_select`` and
    ``city_select``), which are not stored on their own; ``clean`` merges them
    into the ``address`` field.
    """

    state_select = forms.CharField(required=True)
    city_select = forms.CharField(required=True)
    
    class Meta:
        model = Profile
        fields = ['first_name','last_name','address','postal_code',
                  'image','description']
        
    def clean(self):

        """
        Combine state, city and street address into one address string.

        The cleaned ``address`` becomes ``"<state>, <city>, <address>"``; empty parts
        are skipped.

        Returns:
            The cleaned data with the merged ``address``.

        Note:
            The merged value is what gets saved, so submitting an address that
            already contains the state and city would add them a second time.
        """

        cleaned_data = super().clean()
        state = cleaned_data.get('state_select')
        city = cleaned_data.get('city_select')
        address = cleaned_data.get('address')

        cleaned_data['address'] = ', '.join(part for part in (state, city, address) if part)
        return cleaned_data
    

class UserModelForm(forms.ModelForm):

    """Form for editing the phone number, email and username of a user."""
    
    class Meta:
        model = user
        fields = [
            'phone','email','username',
        ]
        
class CustomUserRegisterationForm(UserCreationForm):

    """
    Registration form for the custom user model.

    Extends ``UserCreationForm`` (which adds the password and its confirmation)
    with the phone number, username and email.
    """
    
    class Meta:
        model = user
        fields = ['phone','username','email',]