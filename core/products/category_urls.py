from django.urls import path

from . import category_views as views



urlpatterns = [

    path('',views.CategoryListView.as_view(),name='Category_list'),
    path('<path:category_path>/',views.CategoryListView.as_view(),name='Category_list'),
]