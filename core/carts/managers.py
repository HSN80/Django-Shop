from django.db import models, IntegrityError
from django.core.exceptions import ValidationError

'''
```CartManager``` checks if user already has a active cart,
otherwise create a new cart with active status.
'''

class CartManager(models.Manager):
    
    '''
    Manager for Cart model. checks for active carts so every user can only
    have one active cart at a time.
    '''
    
    def _get_active_cart(self, profile):

        '''
        search for active cart based on the user profile.
        
        args:
            
            profile : user's profile.

        returns:
            
            active cart for the given user. 
        '''

        return self.filter(profile=profile, status='active',).filter()
    
    def _create_active_cart(self, profile):

        '''
        trying to create a new cart with active status if none exists.

        args:
            
            profile : user's profile.        
        '''

        if self.get_active_cart(profile).exists():

            '''
            call get_active_cart for checking.

            raise:

                a validation error and abort creating new cart.
            '''
            
            raise ValidationError(f'کاربر {profile} دارای سبد فعال میباشد.')
        
        try:

            '''
            trying to create new active cart if any key error accours
            raises a IntegrityError and abort.
            '''
            
            return self.create(profile=profile, status='active')
        
        except IntegrityError():
            raise ValidationError('خطا: یک سبد فعال همزمان ساخته شد')
        
