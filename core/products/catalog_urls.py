from django.urls import path
from . import catalog_views as views
urlpatterns = [
    path('',views.CatalogListView.as_view(),name='Catalog_list'),
    path('products/<path:category_path>/<str:slug>/',views.CatalogDetailView.as_view(),name='Catalog_detail'),
]