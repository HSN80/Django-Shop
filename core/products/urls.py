from django.urls import path, include

app_name = 'products'

urlpatterns = [
    path('categorys/',include('products.category_urls')),
    path('comments/',include('products.comment_urls')),
    path('',include('products.catalog_urls')),
]