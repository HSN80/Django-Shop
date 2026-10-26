from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Favorites

# Register your models here.


@admin.register(Favorites)
class FavoritesAdmin(SimpleHistoryAdmin):

    """
    Admin for ``Favorites`` with change history, search and a date filter.

    Favorites can be searched by the user's username or the product title, and
    filtered by creation date. The related user and product are fetched together
    with the list, so the page does not run extra queries per row.
    """

    list_display = ('profile', 'product_id', 'created_date')
    list_select_related = ('profile__user', 'product_id')
    search_fields = ('profile__user__username', 'product_id__title')
    list_filter = ('created_date',)