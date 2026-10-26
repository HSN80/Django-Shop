from django.db import models

class PublishedManager(models.Manager):
    
    """
    Manager that returns only published products.

    Used as ``Catalog.published``, so public pages (home page, category pages,
    product pages) never show drafts.

    Note:
        The model that uses this manager must define a ``Status`` choices class
        with a ``PUBLISHED`` value and a ``status`` field. Use ``Catalog.objects``
        to include drafts, as the admin does.
    """

    def get_queryset(self):

        """Return the base queryset limited to products with the published status."""
        
        return super().get_queryset().filter(status=self.model.Status.PUBLISHED)