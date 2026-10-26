"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from debug_toolbar.toolbar import debug_toolbar_urls
from django.contrib.sitemaps.views import sitemap
from products.sitemaps import CatalogViewSitemap, CategoryViewSitemap

sitemaps = {
    'products': CatalogViewSitemap,
    'categoreis': CategoryViewSitemap
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/",include('accounts.urls')),
    path("accounts/tickets/",include('tickets.urls')),
    path("",include('products.urls',namespace='products')),
    path("fav/",include('userfav.urls')),
    path('carts/',include('carts.urls')),
    path('orders/',include('orders.urls')),
    path('robots.txt/',include('robots.urls')),
    path("sitemap.xml",sitemap,{"sitemaps": sitemaps},
    name="django.contrib.sitemaps.views.sitemap",
)
] + debug_toolbar_urls()

# if settings.MAINTENANCE_MODE:
#    urlpatterns.insert(0, re_path(r'^', TemplateView.as_view(template_name='maintenance.html'), name='maintenance'))

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root= settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root= settings.MEDIA_ROOT)

