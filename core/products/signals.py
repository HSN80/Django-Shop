from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify
import secrets

from .models import Catalog, Category

@receiver(pre_save,sender=Catalog)
def catalog_prepopulated_slug(sender, instance, **kwargs):

    """
    Generate a slug for a product that has none.

    Runs before each ``Catalog`` save. If ``slug`` is empty it is built from the
    title (Unicode letters are kept) followed by a short random suffix, for
    example ``'my-product-3f9a'``. A title with no usable characters falls back to
    ``'product'``. A product that already has a slug is left untouched.

    Args:
        sender: The ``Catalog`` model class.
        instance: The product about to be saved.
        **kwargs: Extra signal arguments; ``raw`` is checked.

    Note:
        The slug is unique, and the 4-character random suffix makes a collision
        unlikely but not impossible.
    """

    if kwargs.get('raw'):
        return 
    
    if not instance.slug:
        slug = slugify(instance.title, allow_unicode=True)

        if not slug:
            slug = 'product'

        random_suffix = secrets.token_hex(2)
        instance.slug = f'{slug}-{random_suffix}'
        

@receiver(pre_save,sender=Category)
def category_prepopulated_slug(sender, instance, **kwargs):

    """
    Generate a slug for a category that has none.

    Runs before each ``Category`` save and builds the slug from the title (Unicode
    letters are kept) when ``slug`` is empty.

    Args:
        sender: The ``Category`` model class.
        instance: The category about to be saved.
        **kwargs: Extra signal arguments; ``raw`` is checked.

    Note:
        ``Category.save`` already sets the slug from the title before this
        signal runs, so the slug is never empty here and this receiver has no
        effect in practice.
    """

    if kwargs.get('raw'):
        return 
    
    if not instance.slug:
        instance.slug = slugify(instance.title, allow_unicode=True)
