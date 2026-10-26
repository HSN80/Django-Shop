from django.contrib import sitemaps
from .models import Catalog, Category

class CatalogViewSitemap(sitemaps.Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return Catalog.objects.all()
    
    def lastmod(self,item):
        return item.updated_date
    
class CategoryViewSitemap(sitemaps.Sitemap):

    priority = 0.5
    changefreq = 'daily'

    def items(self):
        return Category.objects.all()
    
    def location(self, obj):
        return f'/{obj.get_category_path()}/'

    