from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.urls import path, reverse

"""
Custom admin site for the shop.

Replaces Django's default admin site (see ``core.apps.ShopAdminConfig``) to add
a dashboard on the index page, two superuser-only reports (activity and
state-at-date) and a sidebar grouped by function instead of by app.
"""


"""
Sidebar groups for the admin menu.
Each entry is ``(key, title, models)``, where ``models`` lists model labels in
lowercase ``app_label.model_name`` form. The order here is the order in the
menu.

Note:
    Registered models that are not listed here appear in an extra "other"
    group, so a new model is never hidden from the menu.
"""
SECTIONS = (


    ('users', 'کاربران', ('accounts.user', 'accounts.profile', 'auth.group')),
    ('sales', 'فروش', ('orders.order', 'orders.invoice', 'orders.payment', 'carts.cart', 'carts.cartitem')),
    ('catalog', 'محصولات', (
        'products.catalog', 'products.category', 'products.discount',
        'products.image', 'products.comment',
    )),
    ('support', 'پشتیبانی', ('tickets.ticket', 'tickets.message')),
    ('engagement', 'محتوا و تعامل', ('userfav.favorites', 'multimedia.media')),
)


class ShopAdminSite(admin.AdminSite):

    """
    Admin site with a dashboard, reports and a function-based menu.

    Attributes:
        site_header: Title shown at the top of every admin page.
        site_title: Text appended to the browser tab title.
        index_title: Heading of the admin index page.
    """

    site_header = 'مدیریت فروشگاه'
    site_title = 'مدیریت فروشگاه'
    index_title = 'داشبورد'

    def get_urls(self):
        
        """
        Add the report URLs in front of the default admin URLs.

        Adds ``activity/`` (route name ``activity``) and ``state-at/`` (route name
        ``state_at``), both wrapped in ``admin_view`` so only logged-in staff can
        reach them.
        """
        
        return [
            path('activity/', self.admin_view(self.activity_view), name='activity'),
            path('state-at/', self.admin_view(self.state_at_view), name='state_at'),
        ] + super().get_urls()

    def _report_response(self, request, template, title, builder):
        
        """
        Render a report page, for superusers only.

        Args:
            request: The current admin request.
            template: Template used to render the report.
            title: Page title.
            builder: Callable that takes ``request.GET`` and returns the report's
                context dict.

        Returns:
            A ``TemplateResponse`` with the admin context, the title and the data
            returned by ``builder``.

        Raises:
            PermissionDenied: If the user is not a superuser.
        """

        if not request.user.is_superuser:
            raise PermissionDenied
        context = {**self.each_context(request), 'title': title, **builder(request.GET)}
        return TemplateResponse(request, template, context)

    def activity_view(self, request):
        
        """
        Show the activity report: a timeline of changes across all sections.

        The report builder is imported inside the method to avoid loading the models
        while the admin site is being set up.
        """

        from .reports import build_activity
        return self._report_response(request, 'admin/activity.html', 'فعالیت‌ها', build_activity)

    def state_at_view(self, request):
        
        """
        Show the state-at-date report: how a section looked on a chosen day.

        The report builder is imported inside the method to avoid loading the models
        while the admin site is being set up.
        """

        from .reports import build_state
        return self._report_response(request, 'admin/state_at.html', 'وضعیت در تاریخ', build_state)

    def index(self, request, extra_context=None):

        """
        Render the admin index page, with the dashboard for superusers.

        Args:
            request: The current admin request.
            extra_context: Extra template context from the caller.

        Returns:
            The index response. For superusers the context contains ``dashboard``
            (see ``core.dashboard.build_dashboard``); other staff see the default
            index.

        Note:
            The dashboard queries run on every visit to the index page.
        """

        extra_context = extra_context or {}
        if request.user.is_superuser:
            from .dashboard import build_dashboard
            extra_context['dashboard'] = build_dashboard()
        return super().index(request, extra_context)

    def _reports_section(self):

        """
        Build the "reports" menu group in the same format as a model group.

        Returns:
            A dict shaped like an entry of ``get_app_list`` with two view-only
            items: the activity report and the state-at-date report.
        """
        def entry(name, object_name, url_name):
            return {
                'name': name,
                'object_name': object_name,
                'admin_url': reverse(url_name),
                'add_url': None,
                'view_only': True,
                'perms': {'view': True},
            }

        models = [
            entry('فعالیت‌ها', 'Activity', 'admin:activity'),
            entry('وضعیت در تاریخ', 'StateAt', 'admin:state_at'),
        ]
        return {
            'name': 'گزارش‌ها',
            'app_label': 'reports',
            'app_url': models[0]['admin_url'],
            'has_module_perms': True,
            'models': models,
        }

    def get_app_list(self, request, app_label=None):

        """
        Return the sidebar groups, arranged by function instead of by app.

        Models are regrouped according to ``SECTIONS``; models not listed there go
        into an "other" group, and superusers get an extra "reports" group at the
        end.

        Args:
            request: The current admin request.
            app_label: If given (app index pages), the default list for that single
                app is returned unchanged.

        Returns:
            A list of group dicts in the format the admin templates expect.

        Note:
            Only models the user has permission to see are included, so a group
            with no visible models is left out.
        """

        app_list = super().get_app_list(request, app_label)
        if app_label:
            return app_list

        models = {}
        for app in app_list:
            for model in app['models']:
                models[model['model']._meta.label_lower] = model

        result, used = [], set()
        for key, name, labels in SECTIONS:
            items = [models[label] for label in labels if label in models]
            if not items:
                continue
            used.update(label for label in labels if label in models)
            result.append({
                'name': name,
                'app_label': key,
                'app_url': items[0]['admin_url'] or '',
                'has_module_perms': True,
                'models': items,
            })

        rest = [m for label, m in models.items() if label not in used]
        if rest:
            result.append({
                'name': 'سایر',
                'app_label': 'other',
                'app_url': rest[0]['admin_url'] or '',
                'has_module_perms': True,
                'models': rest,
            })

        if request.user.is_superuser:
            result.append(self._reports_section())
        return result