from django.db import models
from simple_history.models import HistoricalRecords

# Create your models here.

class Favorites(models.Model):
    
    """
    A product that a user has added to their favorites.

    Attributes:
        profile: The user who favorited the product; deleting the profile
            deletes the favorite.
        product_id: The favorited product (a foreign key to ``Catalog``, despite
            the ``_id`` in its name; the raw id is ``product_id_id``). Deleting
            the product deletes the favorite.
        created_date: When the product was favorited.
        updated_date: When the record was last saved.

    Note:
        Favorites are ordered by creation date, oldest first. The database does
        not prevent the same product from being favorited twice by one user;
        ``FavoriteCreate`` avoids duplicates with ``get_or_create``.
    """

    profile = models.ForeignKey(
        'accounts.Profile',
        verbose_name = 'کاربر',
        on_delete = models.CASCADE,
        related_name = 'favorites',
    )

    product_id = models.ForeignKey(
        'products.Catalog',
        verbose_name = 'محصول',
        on_delete = models.CASCADE,
        related_name = 'favorites',
    )
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f'{self.profile.user} {self.product_id.title}'
    

    class Meta:
        verbose_name = 'علاقه مندی'
        verbose_name_plural = 'علاقه مندی ها'
        ordering = ('created_date',)
