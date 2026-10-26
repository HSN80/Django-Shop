import os
import tempfile
import requests
from unittest import mock
import json

from datetime import timedelta
from io import StringIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib import admin
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError


from accounts.models import Profile, User
from carts.models import Cart, CartItem
from core.admin_site import SECTIONS
from core.dashboard import build_dashboard
from multimedia.models import Media
from orders.models import Invoice, Order, Payment
from orders.froms import OrderModelForm
from products.models import Catalog, Category, Comment, Discount
from tickets.models import Ticket
from userfav.models import Favorites
from products.admin import CatalogAdminForm
from products.specs import SpecsField, specs_to_groups
from django.contrib.messages import get_messages
PW = 'test-pass-123'
BACKEND = 'django.contrib.auth.backends.ModelBackend'
FAST_HASH = override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])


def phone(n):
    return f'+98912000000{n}'


def make_user(n, **extra):
    user = User(phone=phone(n), username=f'user{n}', email=f'user{n}@x.com', **extra)
    user.set_password(PW)
    user.save()
    Profile.objects.get_or_create(
        user=user, defaults={'first_name': f'first{n}', 'last_name': f'last{n}'},
    )
    return user


def profile_of(user):
    return Profile.objects.get(user=user)


def make_product(category, title, price=1000, stock=5, status=Catalog.Status.PUBLISHED):
    return Catalog.objects.create(
        title=title, slug=title, description='desc', price=price,
        stock=stock, status=status, category=category,
    )


def make_order(profile, price, status='checkout', tracking=None):
    return Order.objects.create(
        profile=profile, first_name='a', last_name='b', address='addr',
        postal_code='123', price=price, status=status, tracking_code=tracking,
    )

class OrderFormTests(TestCase):
    data = {
        'first_name': 'a', 'last_name': 'b', 'address': 'street 1',
        'postal_code': '123', 'state_select': 'Tehran',
        'city_select': 'Tehran', 'terms': 'on',
    }

    def test_review_submission_requires_confirmation(self):
        form = OrderModelForm({**self.data, 'is_review_submission': 'on'})
        self.assertFalse(form.is_valid())
        self.assertIn('confirm_info', form.errors)

    def test_checkout_submission_does_not_require_confirmation(self):
        form = OrderModelForm(self.data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['address'], 'Tehran, Tehran, street 1')

@FAST_HASH
class BaseCase(TestCase):
    """یک ادمین، دو مشتری، یک دسته‌بندی و یک محصول (prod1 با قیمت ۱۰۰۰)"""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user(1, is_staff=True, is_superuser=True)
        cls.customer = make_user(2)
        cls.other = make_user(3)
        cls.category = Category.objects.create(title='cat')
        cls.product = make_product(cls.category, 'prod1')

    def setUp(self):
        self.client.force_login(self.admin, backend=BACKEND)


# ---------------------------------------------------------------- لاگ و تاریخچه

class HistoryTests(BaseCase):

    def test_create_and_change_are_recorded(self):
        records = Catalog.history.filter(id=self.product.id)
        self.assertEqual(records.count(), 1)
        self.assertEqual(records.get().history_type, '+')

        self.product.price = 2000
        self.product.save()
        self.assertEqual(records.count(), 2)
        self.assertEqual(records.order_by('-history_id').first().history_type, '~')

    def test_delete_is_recorded(self):
        product = make_product(self.category, 'to-delete')
        product_id = product.id
        product.delete()
        self.assertTrue(Catalog.history.filter(id=product_id, history_type='-').exists())

    def test_admin_action_records_user_and_reason(self):
        # اگر history_user خالی بود، HistoryRequestMiddleware به MIDDLEWARE اضافه نشده
        draft = make_product(self.category, 'draft1', status=Catalog.Status.DRAFT)
        self.client.post(
            reverse('admin:products_catalog_changelist'),
            {'action': 'publish', '_selected_action': [draft.pk], 'index': 0},
        )
        draft.refresh_from_db()
        self.assertEqual(draft.status, Catalog.Status.PUBLISHED)

        record = Catalog.history.filter(id=draft.id).order_by('-history_id').first()
        self.assertEqual(record.history_user, self.admin)
        self.assertTrue(record.history_change_reason)

    def test_user_history_excludes_secret_fields(self):
        names = {f.name for f in User.history.model._meta.get_fields()}
        self.assertNotIn('password', names)
        self.assertNotIn('last_login', names)


# ---------------------------------------------------------------- صفحه‌های ادمین

class AdminPagesTests(BaseCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        profile = profile_of(cls.customer)
        order = make_order(profile, 1500, 'checkout', 'TRK1')
        Invoice.objects.create(order=order, product=cls.product, quantity=1, purchase_price=1500)
        Ticket.objects.create(profile=profile, subject='help', department='technical', content='c')
        Comment.objects.create(user=profile, product=cls.product, body='nice')
        Discount.objects.create(title='sale', percent=10)
        Favorites.objects.create(profile=profile, product_id=cls.product)
        Media.objects.create(profile=profile, product=cls.product)

    def test_every_changelist_loads(self):
        for model in admin.site._registry:
            opts = model._meta
            url = reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')
            with self.subTest(model=opts.label):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_every_change_page_loads(self):
        skip = {'accounts.user', 'accounts.profile'}  # کاربر system ممکن است اول باشد؛ جدا تست می‌شوند
        for model in admin.site._registry:
            opts = model._meta
            obj = model._default_manager.first()
            if opts.label_lower in skip or obj is None:
                continue
            url = reverse(f'admin:{opts.app_label}_{opts.model_name}_change', args=[obj.pk])
            with self.subTest(model=opts.label):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_user_change_page_links_to_dossier(self):
        response = self.client.get(reverse('admin:accounts_user_change', args=[self.customer.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('admin:accounts_user_dossier', args=[self.customer.pk]))

    def test_catalog_search_does_not_crash(self):
        # قبلاً search_fields شامل فیلد category بود و سرچ خطا می‌داد
        url = reverse('admin:products_catalog_changelist')
        for query in ('prod', 'cat'):
            with self.subTest(q=query):
                response = self.client.get(url, {'q': query})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'prod1')

    def test_order_and_user_search(self):
        orders = self.client.get(reverse('admin:orders_order_changelist'), {'q': 'TRK1'})
        self.assertEqual(orders.context['cl'].result_count, 1)
        users = self.client.get(reverse('admin:accounts_user_changelist'), {'q': 'user2'})
        self.assertEqual(users.context['cl'].result_count, 1)

    def test_sidebar_is_grouped_by_function(self):
        response = self.client.get(reverse('admin:index'))
        keys = {app['app_label'] for app in response.context['available_apps']}
        self.assertTrue({key for key, _, _ in SECTIONS} <= keys)
        self.assertIn('reports', keys)


class CartAdminTests(BaseCase):
    # اگر این کلاس خطا داد، اول CartManager (carts/managers.py) را بررسی کن

    def test_cart_totals_and_abandoned_card(self):
        cart = Cart.objects.create(profile=profile_of(self.customer), status='abandoned')
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.get(reverse('admin:carts_cart_changelist'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2,000')

        abandoned_card = build_dashboard()['cards'][-1]
        self.assertEqual(abandoned_card['value'], 1)
        self.assertEqual(abandoned_card['sub'], '2,000 تومان')


# ---------------------------------------------------------------- داشبورد

class DashboardTests(BaseCase):

    def cards(self):
        return {card['label']: card for card in build_dashboard()['cards']}

    def test_sales_count_only_paid_orders(self):
        profile = profile_of(self.customer)
        make_order(profile, 1000, 'checkout')
        make_order(profile, 500, 'sent')
        make_order(profile, 9999, 'awaiting')
        make_order(profile, 7777, 'canceled')

        cards = self.cards()
        self.assertEqual(cards['فروش امروز']['value'], '1,500 تومان')
        self.assertEqual(cards['فروش ۳۰ روز اخیر']['value'], '1,500 تومان')
        self.assertEqual(cards['منتظر ارسال']['value'], 1)  # فقط checkout

    def test_old_orders_are_outside_30_day_window(self):
        old = make_order(profile_of(self.customer), 3000, 'checkout')
        Order.objects.filter(pk=old.pk).update(created_date=timezone.now() - timedelta(days=40))
        self.assertEqual(self.cards()['فروش ۳۰ روز اخیر']['value'], '0 تومان')

    def test_pending_tickets_card(self):
        ticket = Ticket.objects.create(
            profile=profile_of(self.customer), subject='t', department='technical', content='c',
        )
        self.assertEqual(self.cards()['تیکت نیازمند پاسخ']['value'], 1)

        ticket = Ticket._base_manager.get(pk=ticket.pk)
        ticket.status = 'closed'
        ticket.save()
        self.assertEqual(self.cards()['تیکت نیازمند پاسخ']['value'], 0)

    def test_system_user_is_not_counted(self):
        Ticket.objects.create(  # سیگنال تیکت کاربر system را می‌سازد
            profile=profile_of(self.customer), subject='t', department='technical', content='c',
        )
        self.assertTrue(User.objects.filter(username='system').exists())

        card = self.cards()['کاربر جدید (۷ روز)']
        self.assertEqual(card['value'], 3)
        self.assertEqual(card['sub'], 'از کل 3 کاربر')

    def test_low_stock_table(self):
        make_product(self.category, 'low', stock=2)
        make_product(self.category, 'plenty', stock=50)
        make_product(self.category, 'hidden', stock=0, status=Catalog.Status.DRAFT)
        titles = [p.title for p in build_dashboard()['low_stock']]
        self.assertIn('low', titles)
        self.assertNotIn('plenty', titles)
        self.assertNotIn('hidden', titles)  # پیش‌نویس‌ها نمایش داده نمی‌شوند

    def test_index_renders_dashboard_for_superuser(self):
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('dashboard', response.context)
        self.assertContains(response, 'فروش امروز')

    def test_staff_without_superuser_gets_no_dashboard(self):
        self.client.force_login(make_user(4, is_staff=True), backend=BACKEND)
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('dashboard', response.context)


# ---------------------------------------------------------------- پرونده‌ی کاربر

class DossierTests(BaseCase):

    def url(self, user):
        return reverse('admin:accounts_user_dossier', args=[user.pk])

    def post(self, user, action, reason=''):
        return self.client.post(self.url(user), {'action': action, 'reason': reason})

    def test_ban_blocks_login_and_is_recorded(self):
        self.assertIsNotNone(authenticate(request=None, username=phone(2), password=PW))

        self.post(self.customer, 'ban', 'spam')
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertIsNone(authenticate(request=None, username=phone(2), password=PW))

        record = User.history.filter(id=self.customer.id).order_by('-history_id').first()
        self.assertEqual(record.history_user, self.admin)
        self.assertIn('spam', record.history_change_reason)
        self.assertFalse(record.is_active)
    def test_unban_restores_login(self):
        self.post(self.customer, 'ban')
        self.post(self.customer, 'unban')
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)
        self.assertIsNotNone(authenticate(request=None, username=phone(2), password=PW))

    def test_verify_and_unverify(self):
        self.post(self.customer, 'verify')
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_verified)
        self.post(self.customer, 'unverify')
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_verified)

    def test_cannot_ban_self_or_other_superusers(self):
        boss2 = make_user(5, is_staff=True, is_superuser=True)
        self.post(self.admin, 'ban')
        self.post(boss2, 'ban')
        for user in (self.admin, boss2):
            user.refresh_from_db()
            self.assertTrue(user.is_active)

    def test_unknown_action_is_ignored(self):
        self.post(self.customer, 'delete')
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)

    def test_bulk_ban_skips_superusers(self):
        self.client.post(
            reverse('admin:accounts_user_changelist'),
            {'action': 'ban_users', '_selected_action': [self.customer.pk, self.admin.pk], 'index': 0},
        )
        self.customer.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertTrue(self.admin.is_active)

    def test_page_shows_orders_invoices_and_stats(self):
        profile = profile_of(self.customer)
        order = make_order(profile, 1500, 'checkout', 'TRK9')
        Invoice.objects.create(order=order, product=self.product, quantity=2, purchase_price=750)
        Ticket.objects.create(profile=profile, subject='my-ticket', department='technical', content='c')

        response = self.client.get(self.url(self.customer))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TRK9')
        self.assertContains(response, 'prod1')       # خط فاکتور
        self.assertContains(response, 'my-ticket')

        cards = response.context['dossier']['cards']
        self.assertEqual(cards[0]['value'], 1)                # تعداد سفارش
        self.assertEqual(cards[1]['value'], '1,500 تومان')    # مجموع خرید
        self.assertEqual(cards[2]['value'], 1)                # تیکت باز

    def test_timeline_contains_ban_with_reason(self):
        self.post(self.customer, 'ban', 'spam')
        events = self.client.get(self.url(self.customer)).context['dossier']['events']
        self.assertTrue(any('مسدود' in e['text'] and 'spam' in e['reason'] for e in events))

    def test_system_user_dossier_is_404(self):
        Ticket.objects.create(
            profile=profile_of(self.customer), subject='t', department='technical', content='c',
        )
        system = User.objects.get(username='system')
        self.assertEqual(self.client.get(self.url(system)).status_code, 404)

    def test_non_staff_is_redirected_to_login(self):
        self.client.force_login(self.customer, backend=BACKEND)
        self.assertEqual(self.client.get(self.url(self.other)).status_code, 302)


# ---------------------------------------------------------------- اکشن‌های سفارش و تیکت

class OrderActionTests(BaseCase):

    def post(self, action, *orders):
        return self.client.post(
            reverse('admin:orders_order_changelist'),
            {'action': action, '_selected_action': [o.pk for o in orders], 'index': 0},
        )

    def status(self, order):
        return Order.objects.get(pk=order.pk).status

    def test_mark_sent_needs_paid_status_and_tracking_code(self):
        profile = profile_of(self.customer)
        ok = make_order(profile, 100, 'checkout', 'T-OK')
        no_code = make_order(profile, 100, 'checkout', None)
        unpaid = make_order(profile, 100, 'awaiting', 'T-UNPAID')

        self.post('mark_sent', ok, no_code, unpaid)
        self.assertEqual(self.status(ok), 'sent')
        self.assertEqual(self.status(no_code), 'checkout')
        self.assertEqual(self.status(unpaid), 'awaiting')

        record = Order.history.filter(id=ok.id).order_by('-history_id').first()
        self.assertEqual(record.history_user, self.admin)
        self.assertTrue(record.history_change_reason)

    def test_mark_arrived_only_from_sent(self):
        profile = profile_of(self.customer)
        sent = make_order(profile, 100, 'sent', 'T-1')
        paid = make_order(profile, 100, 'checkout', 'T-2')
        self.post('mark_arrived', sent, paid)
        self.assertEqual(self.status(sent), 'arrived')
        self.assertEqual(self.status(paid), 'checkout')

    def test_comment_approve_and_reject(self):
        comment = Comment.objects.create(user=profile_of(self.customer), product=self.product, body='b')
        url = reverse('admin:products_comment_changelist')
        self.client.post(url, {'action': 'approve', '_selected_action': [comment.pk], 'index': 0})
        comment.refresh_from_db()
        self.assertEqual(comment.status, 'approved')
        self.client.post(url, {'action': 'reject', '_selected_action': [comment.pk], 'index': 0})
        comment.refresh_from_db()
        self.assertEqual(comment.status, 'rejected')


class TicketAdminTests(BaseCase):

    def setUp(self):
        super().setUp()
        self.ticket = Ticket.objects.create(
            profile=profile_of(self.customer), subject='tkt', department='technical', content='c',
        )
        self.url = reverse('admin:tickets_ticket_changelist')

    def fetch(self):
        return Ticket._base_manager.get(pk=self.ticket.pk)

    def test_closed_ticket_stays_visible(self):
        ticket = self.fetch()
        ticket.status = 'closed'
        ticket.save()
        response = self.client.get(self.url)
        self.assertEqual(response.context['cl'].result_count, 1)
        self.assertContains(response, 'tkt')

    def test_bulk_delete_is_disabled(self):
        self.client.post(self.url, {
            'action': 'delete_selected', '_selected_action': [self.ticket.pk],
            'index': 0, 'post': 'yes',
        })
        self.assertTrue(Ticket._base_manager.filter(pk=self.ticket.pk).exists())

    def test_close_and_reopen_actions(self):
        data = {'_selected_action': [self.ticket.pk], 'index': 0}
        self.client.post(self.url, {**data, 'action': 'close_tickets'})
        ticket = self.fetch()
        self.assertEqual((ticket.status, ticket.is_archived), ('closed', True))

        self.client.post(self.url, {**data, 'action': 'reopen_tickets'})
        ticket = self.fetch()
        self.assertEqual((ticket.status, ticket.is_archived), ('open', False))


# ---------------------------------------------------------------- گزارش‌ها

class ReportsTests(BaseCase):

    def activity(self, **params):
        return self.client.get(reverse('admin:activity'), params)

    def test_activity_shows_old_and_new_values(self):
        self.product.price = 2000
        self.product.save()
        events = self.activity(section='catalog').context['events']
        edits = [e for e in events if e['kind_key'] == '~' and 'prod1' in e['object']]
        self.assertEqual(len(edits), 1)
        self.assertIn(('1000', '2000'), [(old, new) for _, old, new in edits[0]['changes']])

    def test_activity_action_filter(self):
        self.product.price = 2000
        self.product.save()
        events = self.activity(section='catalog', action='+').context['events']
        self.assertTrue(events)
        self.assertEqual({e['kind_key'] for e in events}, {'+'})

    def test_activity_actor_filter(self):
        draft = make_product(self.category, 'draft1', status=Catalog.Status.DRAFT)
        self.client.post(
            reverse('admin:products_catalog_changelist'),
            {'action': 'publish', '_selected_action': [draft.pk], 'index': 0},
        )
        events = self.activity(by='staff').context['events']
        self.assertTrue(events)
        self.assertTrue(all(self.admin.username in e['by'] for e in events))

    def test_login_noise_is_hidden(self):
        self.customer.last_login = timezone.now()
        self.customer.save(update_fields=['last_login'])
        events = self.activity(section='users').context['events']
        self.assertEqual([e for e in events if e['kind_key'] == '~'], [])

    def test_reports_require_superuser(self):
        self.client.force_login(make_user(4, is_staff=True), backend=BACKEND)
        for name in ('admin:activity', 'admin:state_at'):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def state(self, days_ago=0, section='products'):
        day = (timezone.localdate() - timedelta(days=days_ago)).isoformat()
        return self.client.get(reverse('admin:state_at'), {'section': section, 'date': day})

    def test_state_today_lists_current_products(self):
        response = self.state()
        self.assertEqual(response.context['count'], 1)
        self.assertContains(response, 'prod1')
        self.assertFalse(response.context['before_logging'])

    def test_state_before_logging_started_warns(self):
        response = self.state(days_ago=1)
        self.assertTrue(response.context['before_logging'])
        self.assertEqual(response.context['count'], 0)

    def test_state_reconstructs_past_values(self):
        # نسخه‌ی اول را ۵ روز عقب می‌بریم، بعد قیمت را عوض می‌کنیم
        Catalog.history.filter(id=self.product.id).update(
            history_date=timezone.now() - timedelta(days=5),
        )
        self.product.price = 2000
        self.product.save()

        self.assertEqual(self.state(days_ago=2).context['rows'][0][1], '1,000')
        self.assertEqual(self.state(days_ago=0).context['rows'][0][1], '2,000')

    def test_state_hides_deleted_objects(self):
        make_product(self.category, 'gone').delete()
        titles = [row[0] for row in self.state().context['rows']]
        self.assertIn('prod1', titles)
        self.assertNotIn('gone', titles)


# ---------------------------------------------------------------- مدل‌ها و migrationها

class CategoryPathTests(TestCase):

    def test_paths_for_root_child_and_grandchild(self):
        a = Category.objects.create(title='a')
        b = Category.objects.create(title='b', parent=a)
        c = Category.objects.create(title='c', parent=b)
        self.assertEqual(a.get_category_path(), 'a')
        self.assertEqual(b.get_category_path(), 'a/b')
        self.assertEqual(c.get_category_path(), 'a/b/c')


class MigrationTests(TestCase):

    def test_no_missing_migrations(self):
        out = StringIO()
        try:
            call_command('makemigrations', check=True, dry_run=True, stdout=out, stderr=out)
        except SystemExit:
            self.fail('migration جاافتاده دارید:\n' + out.getvalue())

# ---------------------------------------------------------------- سیگنال ویدیو

def fake_video_reader(duration):
    def reader(path):
        yield {'duration': duration}
    return reader


class MediaSignalTests(BaseCase):

    def create_media(self, **extra):
        return Media.objects.create(
            profile=profile_of(self.customer), product=self.product, **extra,
        )

    def upload(self, duration):
        with mock.patch('multimedia.signals.read_frames', fake_video_reader(duration)):
            return self.create_media(video=SimpleUploadedFile('clip.mp4', b'data'))

    def test_media_without_video_is_saved(self):
        media = self.create_media()
        self.assertFalse(Media.objects.get(pk=media.pk).is_story)

    def test_short_video_becomes_story_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            media = self.upload(10)
        self.assertTrue(Media.objects.get(pk=media.pk).is_story)

        record = Media.history.filter(id=media.id).order_by('-history_id').first()
        self.assertTrue(record.is_story)
        self.assertTrue(record.history_change_reason)

    def test_long_video_stays_normal(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            media = self.upload(30)
        self.assertFalse(Media.objects.get(pk=media.pk).is_story)

    def test_unreadable_video_is_removed_with_its_file(self):
        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            with mock.patch('multimedia.signals.read_frames', side_effect=RuntimeError('bad')):
                self.create_media(video=SimpleUploadedFile('bad.mp4', b'data'))
            leftovers = [f for _, _, files in os.walk(tmp) for f in files]

        self.assertEqual(Media.objects.count(), 0)
        self.assertEqual(leftovers, [])

class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def fake_zibal(verify=None, request=None):
    """Replacement for requests.post: answers the request and verify endpoints."""
    def post(url, json=None, timeout=None):
        if url.endswith('/request'):
            return FakeResponse(request or {'result': 100, 'trackId': 12345, 'message': 'success'})
        return FakeResponse(verify)
    return post


# ---------------------------------------------------------------- پرداخت

class PaymentTests(BaseCase):
    # product price is 1000 Toman, so a cart of 2 items costs 2000 Toman = 20000 Rial

    def setUp(self):
        super().setUp()
        self.profile = profile_of(self.customer)
        self.cart = Cart.objects.create(profile=self.profile, status='active')
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.order = Order.objects.create(
            profile=self.profile, cart=self.cart, first_name='a', last_name='b',
            address='addr', postal_code='123', price=2000,
        )
        self.cart.status = 'updating'
        self.cart.save(update_fields=['status'])
        self.client.force_login(self.customer, backend=BACKEND)

    def start(self):
        with mock.patch('orders.zibal.requests.post', fake_zibal()):
            return self.client.get(reverse('orders:pay', args=[self.order.pk]))

    def callback(self, verify, track_id=12345):
        with mock.patch('orders.zibal.requests.post', fake_zibal(verify=verify)):
            return self.client.get(reverse('orders:verify'), {'trackId': track_id})

    def paid_reply(self, **extra):
        return {'result': 100, 'amount': 20000, 'refNumber': 777, 'status': 1, **extra}

    def test_start_redirects_to_gateway_and_records_payment(self):
        response = self.start()
        self.assertRedirects(
            response, 'https://gateway.zibal.ir/start/12345', fetch_redirect_response=False,
        )
        payment = Payment.objects.get()
        self.assertEqual(payment.amount, 20000)  # Toman converted to Rial
        self.assertEqual(payment.track_id, 12345)
        self.assertEqual(payment.status, Payment.PENDING)

    def test_start_marks_payment_failed_when_gateway_is_down(self):
        with mock.patch('orders.zibal.requests.post', side_effect=requests.ConnectionError('down')):
            response = self.client.get(reverse('orders:pay', args=[self.order.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Payment.objects.get().status, Payment.FAILED)

    def test_start_refuses_when_stock_is_not_enough(self):
        Catalog.objects.filter(pk=self.product.pk).update(stock=1)
        response = self.start()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Payment.objects.exists())

    def test_cannot_pay_someone_elses_order(self):
        self.client.force_login(self.other, backend=BACKEND)
        self.assertEqual(self.start().status_code, 404)

    def test_successful_payment_completes_the_order(self):
        self.start()
        response = self.callback(self.paid_reply())
        payment = Payment.objects.get()
        self.assertRedirects(
            response, reverse('orders:result', args=[payment.pk]), fetch_redirect_response=False,
        )

        self.assertEqual(payment.status, Payment.PAID)
        self.assertEqual(payment.ref_number, '777')
        self.order.refresh_from_db()
        self.cart.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.status, 'checkout')
        self.assertEqual(self.cart.status, 'checkout')
        self.assertEqual(self.product.stock, 3)

        line = Invoice.objects.get(order=self.order)
        self.assertEqual((line.product, line.quantity, line.purchase_price), (self.product, 2, 1000))

    def test_repeated_callback_does_not_duplicate_anything(self):
        self.start()
        self.callback(self.paid_reply())
        self.callback(self.paid_reply(result=201))
        self.product.refresh_from_db()
        self.assertEqual(Invoice.objects.filter(order=self.order).count(), 1)
        self.assertEqual(self.product.stock, 3)

    def test_failed_payment_cancels_the_order_and_returns_the_cart(self):
        self.start()
        self.callback({'result': 202, 'status': 3})
        self.order.refresh_from_db()
        self.cart.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(Payment.objects.get().status, Payment.FAILED)
        self.assertEqual(self.order.status, 'canceled')
        self.assertEqual(self.cart.status, 'active')
        self.assertEqual(self.product.stock, 5)
        self.assertFalse(Invoice.objects.exists())
    def test_amount_mismatch_is_rejected(self):
        self.start()
        self.callback(self.paid_reply(amount=1000))
        self.order.refresh_from_db()
        self.assertEqual(Payment.objects.get().status, Payment.FAILED)
        self.assertEqual(self.order.status, 'awaiting')

    def test_gateway_down_during_verify_leaves_payment_pending(self):
        self.start()
        with mock.patch('orders.zibal.requests.post', side_effect=requests.ConnectionError('down')):
            self.client.get(reverse('orders:verify'), {'trackId': 12345})
        self.assertEqual(Payment.objects.get().status, Payment.PENDING)

        self.callback(self.paid_reply())  # a later retry completes it
        self.assertEqual(Payment.objects.get().status, Payment.PAID)

    def test_callback_with_bad_or_unknown_track_id(self):
        for track_id in ('abc', '', '999'):
            with self.subTest(track_id=track_id):
                response = self.callback(self.paid_reply(), track_id=track_id)
                self.assertEqual(response.status_code, 302)
        self.assertFalse(Payment.objects.exists())

    def test_result_page_is_private(self):
        self.start()
        payment = Payment.objects.get()
        self.assertEqual(self.client.get(reverse('orders:result', args=[payment.pk])).status_code, 200)
        self.client.force_login(self.other, backend=BACKEND)
        self.assertEqual(self.client.get(reverse('orders:result', args=[payment.pk])).status_code, 404)


class CheckoutTests(BaseCase):

    def test_checkout_links_order_to_profile_and_cart_then_goes_to_payment(self):
        profile = profile_of(self.customer)
        cart = Cart.objects.create(profile=profile, status='active')
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        self.client.force_login(self.customer, backend=BACKEND)

        response = self.client.post(reverse('orders:checkout'), {
            'first_name': 'a', 'last_name': 'b', 'address': 'street 1',
            'postal_code': '123', 'state_select': 'Tehran',
            'city_select': 'Tehran', 'terms': 'on',
        })

        order = Order.objects.get()
        self.assertEqual((order.profile, order.cart, order.price), (profile, cart, 2000))
        self.assertEqual(order.status, 'awaiting')
        cart.refresh_from_db()
        self.assertEqual(cart.status, 'updating')
        self.assertRedirects(response, reverse('orders:pay', args=[order.pk]), fetch_redirect_response=False)

# ---------------------------------------------------------------- ویرایشگر مشخصات

class SpecsEditorTests(BaseCase):

    def editor_data(self):
        return json.dumps([
            {'title': 'ابعاد', 'rows': [{'key': 'طول', 'value': '12'}, {'key': '', 'value': ''}]},
            {'title': 'وزن', 'rows': [{'key': 'خالص', 'value': '1 کیلو'}]},
        ], ensure_ascii=False)

    def test_field_converts_editor_data_to_stored_specs(self):
        self.assertEqual(
            SpecsField().clean(self.editor_data()),
            {'ابعاد': {'طول': '12'}, 'وزن': {'خالص': '1 کیلو'}},
        )

    def test_empty_editor_gives_empty_specs(self):
        for empty in ('', '[]'):
            self.assertEqual(SpecsField().clean(empty), {})

    def test_field_rejects_bad_data(self):
        bad = {
            'missing value': [{'title': 'A', 'rows': [{'key': 'k', 'value': ''}]}],
            'missing name': [{'title': 'A', 'rows': [{'key': '', 'value': 'v'}]}],
            'repeated name': [{'title': 'A', 'rows': [{'key': 'k', 'value': '1'}, {'key': 'k', 'value': '2'}]}],
            'repeated group': [
                {'title': 'A', 'rows': [{'key': 'k', 'value': '1'}]},
                {'title': 'A', 'rows': [{'key': 'j', 'value': '1'}]},
            ],
            'group without title': [{'title': '', 'rows': [{'key': 'k', 'value': '1'}]}],
        }
        for name, data in bad.items():
            with self.subTest(name):
                with self.assertRaises(ValidationError):
                    SpecsField().clean(json.dumps(data))

    def test_old_flat_specs_load_into_a_general_group(self):
        groups = specs_to_groups({'رنگ': 'قرمز', 'ابعاد': {'طول': '12'}})
        self.assertEqual(groups[0]['rows'], [{'key': 'رنگ', 'value': 'قرمز'}])
        self.assertEqual(groups[1]['title'], 'ابعاد')

    def test_change_page_shows_the_editor_with_existing_specs(self):
        Catalog.objects.filter(pk=self.product.pk).update(specs={'ابعاد': {'طول': '12'}})
        response = self.client.get(reverse('admin:products_catalog_change', args=[self.product.pk]))
        self.assertContains(response, 'class="specs-editor"')
        self.assertContains(response, 'ابعاد')

    def test_editor_offers_names_used_by_other_products(self):
        other = make_product(self.category, 'prod2')
        Catalog.objects.filter(pk=other.pk).update(specs={'ابعاد': {'طول': '1', 'عرض': '2'}})
        suggestions = CatalogAdminForm(instance=self.product).fields['specs'].widget.suggestions
        self.assertEqual(suggestions['groups'], ['ابعاد'])
        self.assertCountEqual(suggestions['keys']['ابعاد'], ['طول', 'عرض'])

    def test_editor_escapes_hostile_text(self):
        Catalog.objects.filter(pk=self.product.pk).update(
            specs={'<script>alert(1)</script>': {'"><img src=x>': 'v'}},
        )
        response = self.client.get(reverse('admin:products_catalog_change', args=[self.product.pk]))
        self.assertNotContains(response, '<img src=x>')
        self.assertNotContains(response, '<script>alert(1)</script>')