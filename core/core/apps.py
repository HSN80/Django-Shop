from django.contrib.admin.apps import AdminConfig

"""App configuration that swaps in the custom admin site."""

class ShopAdminConfig(AdminConfig):
    
    """App configuration that swaps in the custom admin site."""

    default_site = 'core.admin_site.ShopAdminSite'