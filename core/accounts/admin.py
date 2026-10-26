from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .dossier import build_dossier
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count, Q, Sum
from simple_history.admin import SimpleHistoryAdmin

from orders.models import Order
from .models import User, Profile

# Register your models here.

"""Actions available on the user dossier page.

Maps the submitted action name to ``(field, new_value, history_label)``.
"""
DOSSIER_ACTIONS = {

    'ban': ('is_active', False, 'حساب مسدود شد'),
    'unban': ('is_active', True, 'مسدودی حساب برداشته شد'),
    'verify': ('is_verified', True, 'کاربر تأیید شد'),
    'unverify': ('is_verified', False, 'تأیید کاربر لغو شد'),
    }

class CustomuserAdmin(SimpleHistoryAdmin, UserAdmin):
    
    """Admin for the custom ``User`` model.

    Extends Django's ``UserAdmin`` with change history (``SimpleHistoryAdmin``),
    per-user order statistics, bulk ban/verify actions and a link to the user
    dossier page.

    Note:
        Every ban, unban, verify and unverify goes through ``save()`` with a
        change reason, so it shows up in the user's history. The ``system`` user
        is excluded from the queryset.
    """

    model = User
    list_display = (
        'username', 'phone', 'email', 'is_verified', 'is_active',
        'orders_count', 'total_spent', 'created_date', 'dossier_link'
    )

    readonly_fields = ('dossier_link',)
    list_filter = ('is_verified', 'is_active', 'is_staff', 'created_date')
    search_fields = (
        'username', 'phone', 'email',
        'profile__first_name', 'profile__last_name',
    )
    ordering = ('-id',)
    actions = ['ban_users', 'unban_users', 'verify_users', 'unverify_users']

    fieldsets = (
    ('Dossier', {'fields': ('dossier_link',)}),
    ('Authentication', {'fields': ('phone', 'password')}),
    ('Info', {'fields': ('username', 'email')}),
    ('Permissions', {
        'fields': (
            'is_staff', 'is_superuser', 'is_active', 'is_verified',
            'groups', 'user_permissions',
        ),
    }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'phone', 'password1', 'password2',
                'username', 'email', 'is_staff',
                'is_superuser', 'is_active', 'is_verified',
            ),
        }),
    )

    def get_queryset(self, request):

        """
        Return the user queryset annotated with order statistics.

        Adds ``orders_count`` (all orders) and ``total_spent`` (sum of paid orders
        only, see ``Order.PAID_STATUSES``). The internal ``system`` user is excluded.
        """

        paid = Q(profile__order__status__in=Order.PAID_STATUSES)
        return (
            super().get_queryset(request)
            .exclude(username='system')
            .annotate(
                orders_count=Count('profile__order', distinct=True),
                total_spent=Sum('profile__order__price', filter=paid),
            )
        )
    
    @admin.display(description='سفارش‌ها', ordering='orders_count')
    def orders_count(self, obj):

        """
        Show the number of orders, taken from the ``orders_count`` annotation.
        """

        return obj.orders_count

    @admin.display(description='مجموع خرید', ordering='total_spent')
    def total_spent(self, obj):

        """
        Show the total of paid orders with thousands separators (0 if none).
        """
        
        return f'{obj.total_spent or 0:,}'

    def get_urls(self):

        """
        Add the ``<id>/dossier/`` URL in front of the default admin URLs.

        The route is named ``accounts_user_dossier`` and is wrapped in
        ``admin_view``, so only staff members can reach it.
        """

        info = self.opts.app_label, self.opts.model_name
        return [
        path(
            '<path:object_id>/dossier/',
            self.admin_site.admin_view(self.dossier_view),
            name='%s_%s_dossier' % info,
        ),
        ] + super().get_urls()

    @admin.display(description='پرونده')
    def dossier_link(self, obj):

        """
        Render a link to the user's dossier page (list and change form).
        """

        url = reverse('admin:accounts_user_dossier', args=[obj.pk])
        return format_html('<a href="{}">مشاهده پرونده</a>', url)

    def dossier_view(self, request, object_id):

        """
        Show a user's dossier page and handle its action form.

        GET renders the dossier: orders with invoice lines, carts, tickets, comments,
        favorites, media and a history timeline. POST applies one of
        ``DOSSIER_ACTIONS`` and redirects back to the page.

        Args:
            request: The current admin request.
            object_id: Primary key of the user, taken from the URL.

        Returns:
            A ``TemplateResponse`` for GET, or a redirect to the same page after POST.

        Raises:
            Http404: If the user does not exist or is the hidden ``system`` user.
            PermissionDenied: If the staff member lacks view permission, or tries to
                POST without change permission.
        """

        user = self.get_object(request, unquote(object_id))
        if user is None:
            raise Http404
        if not self.has_view_or_change_permission(request, user):
            raise PermissionDenied
        can_change = self.has_change_permission(request, user)

        if request.method == 'POST':
            if not can_change:
                raise PermissionDenied
            self._dossier_action(request, user)
            return HttpResponseRedirect(request.path)

        context = {
            **self.admin_site.each_context(request),
            'opts': self.opts,
            'original': user,
            'title': f'پرونده‌ی {user.username}',
            'can_change': can_change,
            'dossier': build_dossier(user),
        }
        return TemplateResponse(request, 'admin/accounts/user/dossier.html', context)

    def _dossier_action(self, request, user):

        """
        Apply a ban, unban, verify or unverify action from the dossier page.

        The optional ``reason`` is stored in the history record (truncated to the
        100-character column) and in the admin log.

        Note:
            Superusers and the logged-in staff member cannot be banned. Nothing is
            saved if the user is already in the requested state.
        """

        action = DOSSIER_ACTIONS.get(request.POST.get('action'))
        if action is None:
            return
        field, value, label = action
        if field == 'is_active' and not value and (user.is_superuser or user.pk == request.user.pk):
            self.message_user(request, 'این حساب را نمی‌شود مسدود کرد.', messages.ERROR)
            return
        if getattr(user, field) == value:
            self.message_user(request, 'وضعیت کاربر از قبل همین بود.', messages.WARNING)
            return

        reason = request.POST.get('reason', '').strip()
        text = f'{label}: {reason}' if reason else label
        setattr(user, field, value)
        user._change_reason = text[:100]  # طول ستون history_change_reason
        user.save(update_fields=[field, 'updated_date'])
        self.log_change(request, user, text)
        self.message_user(request, f'{label}.')

    def _set_flag(self, request, queryset, field, value, reason):

        """
        Set a boolean field on every user in the queryset (bulk-action helper).

        Args:
            request: The current admin request.
            queryset: The selected users.
            field: Boolean field to change (``is_active`` or ``is_verified``).
            value: The new value.
            reason: Change reason stored in the history record.

        Note:
            Users are saved one by one so that history is recorded. When banning,
            superusers and the current user are skipped.
        """

        if field == 'is_active' and not value:
            queryset = queryset.exclude(is_superuser=True).exclude(pk=request.user.pk)
        changed = 0
        for user in queryset:
            if getattr(user, field) != value:
                setattr(user, field, value)
                user._change_reason = reason
                user.save(update_fields=[field, 'updated_date'])
                changed += 1
        self.message_user(request, f'{changed} کاربر تغییر کرد.')

    @admin.action(description='مسدود کردن کاربران انتخاب‌شده')
    def ban_users(self, request, queryset):
        self._set_flag(request, queryset, 'is_active', False, 'مسدود شد')

    @admin.action(description='بازکردن حساب کاربران انتخاب‌شده')
    def unban_users(self, request, queryset):
        self._set_flag(request, queryset, 'is_active', True, 'مسدودی برداشته شد')

    @admin.action(description='تأیید کاربران انتخاب‌شده')
    def verify_users(self, request, queryset):
        self._set_flag(request, queryset, 'is_verified', True, 'تأیید شد')

    @admin.action(description='لغو تأیید کاربران انتخاب‌شده')
    def unverify_users(self, request, queryset):
        self._set_flag(request, queryset, 'is_verified', False, 'تأیید لغو شد')


@admin.register(Profile)
class ProfileAdmin(SimpleHistoryAdmin):

    """
    Admin for ``Profile`` with search, change history and an order count.

    The profile of the internal ``system`` user is hidden.
    """

    list_display = ('user', 'first_name', 'last_name', 'orders_count', 'created_date')
    search_fields = ('user__username', 'user__phone', 'first_name', 'last_name')
    list_select_related = ('user',)
    raw_id_fields = ('user',)

    def get_queryset(self, request):

        """
        Return profiles annotated with ``orders_count``, without the system profile.
        """

        return (
            super().get_queryset(request)
            .exclude(user__username='system')
            .annotate(orders_count=Count('order'))
        )

    @admin.display(description='سفارش‌ها', ordering='orders_count')
    def orders_count(self, obj):

        """
        Show the number of orders, taken from the ``orders_count`` annotation.
        """

        return obj.orders_count


admin.site.register(User, CustomuserAdmin)