from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Media

# Register your models here.

@admin.register(Media)
class MediaAdmin(SimpleHistoryAdmin):

    """
    Admin for ``Media`` with change history, filters and search.

    Media can be filtered by story and highlight status and by date, and searched
    by uploader username or product title.

    Note:
        The admin form runs ``Media.clean``, so a media cannot be marked as
        highlighted unless it is also a story.
    """

    list_display = ('id', 'profile', 'product', 'is_story', 'is_highlighted', 'created_date')
    list_filter = ('is_story', 'is_highlighted', 'created_date')
    list_select_related = ('profile__user', 'product')
    search_fields = ('profile__user__username', 'product__title')