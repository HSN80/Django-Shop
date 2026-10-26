from itertools import groupby
from django.db.models import Count, Prefetch
from carts.models import Cart, CartItem
from orders.models import Invoice, Order
from products.models import Comment
from tickets.models import Ticket

"""
Data builder for the user dossier page in the admin.

Collects a user's orders, carts, tickets, comments, favorites and media, and
builds a history timeline from the ``simple_history`` records of the user,
profile, orders, tickets and comments.
"""



"""
Tracked fields mapped to the labels shown in the timeline.

Only changes to these fields (plus ``is_active`` and ``is_verified`` for users)
produce timeline events.
"""
USER_FIELDS = {
    'username': 'نام کاربری',
    'email': 'ایمیل',
    'phone': 'تلفن',
    'is_staff': 'دسترسی ادمین',
    'is_superuser': 'سوپریوزر',
}
PROFILE_FIELDS = {
    'first_name': 'نام',
    'last_name': 'نام خانوادگی',
    'address': 'آدرس',
    'postal_code': 'کدپستی',
    'description': 'توضیحات',
    'image': 'تصویر',
}

"""Maximum number of timeline events returned (newest first)."""
MAX_EVENTS = 150


def _walk(records, fields):

    """
    Compare consecutive history records of one object.

    Args:
        records: History records of a single object, oldest first.
        fields: Names of the fields to compare.
    
    Yields:
        ``(previous, current, changed_fields)`` tuples. For the first record
        ``previous`` is ``None`` and ``changed_fields`` is empty.
    """

    prev = None
    for rec in records:
        changed = [] if prev is None else [f for f in fields if getattr(prev, f) != getattr(rec, f)]
        yield prev, rec, changed
        prev = rec


def _who(rec, user):

    """
    Return who made a change, as a label for the timeline.

    Returns:
        ``'سیستم'`` if no user was recorded, ``'خود کاربر'`` if the dossier's own
        user made the change, otherwise the username of the staff member.
    """

    if rec.history_user_id is None:
        return 'سیستم'
    if rec.history_user_id == user.pk:
        return 'خود کاربر'
    return rec.history_user.username


def _event(rec, user, text, created=False):

    """
    Build one timeline event from a history record.

    Args:
        rec: The history record.
        user: The user whose dossier is being built.
        text: Description of the event.
        created: Whether this is the object's creation record.

    Returns:
        A dict with ``date``, ``text``, ``by`` and ``reason`` keys.

    Note:
        Creation events use the object's own ``created_date`` and have no author
        or reason. Records seeded by ``populate_history`` are dated on the day
        history was installed, not on the day the object was created.
    """

    date = rec.created_date if created else rec.history_date
    return {
        'date': date,
        'text': text,
        'by': '' if created else _who(rec, user),
        'reason': '' if created else (rec.history_change_reason or ''),
    }


def _ordered(history_qs):

    """Order history records oldest first and fetch their authors in one query."""

    return history_qs.select_related('history_user').order_by('history_date', 'history_id')


def _user_events(user):

    """
    Build timeline events from the user's own history.

    Detects registration, ban and unban (``is_active``), verification changes
    (``is_verified``) and edits to the fields in ``USER_FIELDS``. Saves that
    change none of these (for example a login updating ``last_login``) produce
    no event.
    """

    events = []
    fields = ['is_active', 'is_verified', *USER_FIELDS]
    for prev, rec, changed in _walk(_ordered(user.history.all()), fields):
        if prev is None:
            events.append(_event(rec, user, 'ثبت‌نام کرد', created=True))
            continue
        texts = []
        if 'is_active' in changed:
            texts.append('حساب مسدود شد' if not rec.is_active else 'مسدودی حساب برداشته شد')
        if 'is_verified' in changed:
            texts.append('کاربر تأیید شد' if rec.is_verified else 'تأیید کاربر لغو شد')
        others = [USER_FIELDS[f] for f in USER_FIELDS if f in changed]
        if others:
            texts.append('ویرایش ' + '، '.join(others))
        events.extend(_event(rec, user, t) for t in texts)
    return events


def _profile_events(profile, user):

    """
    Build timeline events for edits to the user's profile.

    Lists the changed fields from ``PROFILE_FIELDS``. Profile creation is skipped
    because it is covered by the registration event.
    """

    events = []
    for prev, rec, changed in _walk(_ordered(profile.history.all()), PROFILE_FIELDS):
        if prev is None or not changed:
            continue
        names = '، '.join(PROFILE_FIELDS[f] for f in PROFILE_FIELDS if f in changed)
        events.append(_event(rec, user, f'پروفایل ویرایش شد: {names}'))
    return events


def _grouped(history_model, **lookup):

    """
    Yield the history of each object separately.

    Args:
        history_model: A model that has a ``simple_history`` manager.
        **lookup: Filters applied to the history table (for example ``profile_id=1``).

    Yields:
        ``(object_id, records)`` pairs, with each object's records oldest first.
    """

    qs = (
        history_model.history.filter(**lookup)
        .select_related('history_user')
        .order_by('id', 'history_id')
    )
    for object_id, group in groupby(qs, key=lambda r: r.id):
        yield object_id, group


def _order_events(profile, user):

    """
    Build timeline events for the profile's orders.

    Covers order creation, status changes and the moment a tracking code is set.
    """

    events = []
    names = dict(Order.STATUS_CHOICE)
    for order_id, group in _grouped(Order, profile_id=profile.pk):
        for prev, rec, changed in _walk(group, ['status', 'tracking_code']):
            if prev is None:
                events.append(_event(rec, user, f'سفارش #{order_id} ثبت شد ({rec.price:,} تومان)', created=True))
                continue
            if 'status' in changed:
                old, new = names.get(prev.status, prev.status), names.get(rec.status, rec.status)
                events.append(_event(rec, user, f'سفارش #{order_id}: وضعیت از «{old}» به «{new}» تغییر کرد'))
            if 'tracking_code' in changed:
                events.append(_event(rec, user, f'سفارش #{order_id}: کد رهگیری ثبت شد'))
    return events


def _ticket_events(profile, user):

    """
    Build timeline events for the profile's tickets.

    Covers ticket creation and status changes.

    Note:
        A new ticket moves to ``progress`` immediately because of the automatic
        system reply, so it usually has a status-change event right after its
        creation event.
    """

    events = []
    names = dict(Ticket.STATUS_CHOICE)
    for ticket_id, group in _grouped(Ticket, profile_id=profile.pk):
        for prev, rec, changed in _walk(group, ['status']):
            if prev is None:
                events.append(_event(rec, user, f'تیکت «{rec.subject}» ثبت شد', created=True))
            elif changed:
                old, new = names.get(prev.status, prev.status), names.get(rec.status, rec.status)
                events.append(_event(rec, user, f'تیکت «{rec.subject}»: وضعیت از «{old}» به «{new}» تغییر کرد'))
    return events


def _comment_events(profile, user):

    """
    Build timeline events for the profile's comments.

    Covers comment creation and status changes (approval or rejection).
    """

    events = []
    names = dict(Comment.STATUS_CHOICES)
    for comment_id, group in _grouped(Comment, user_id=profile.pk):
        for prev, rec, changed in _walk(group, ['status']):
            if prev is None:
                events.append(_event(rec, user, f'نظر #{comment_id} ثبت شد', created=True))
            elif changed:
                old, new = names.get(prev.status, prev.status), names.get(rec.status, rec.status)
                events.append(_event(rec, user, f'نظر #{comment_id}: وضعیت از «{old}» به «{new}» تغییر کرد'))
    return events


def build_dossier(user):

    """
    Collect everything shown on a user's dossier page.

    Args:
        user: A user fetched through ``CustomuserAdmin.get_queryset``, so that the
            ``orders_count`` and ``total_spent`` annotations are available
            (both default to 0 if missing).

    Returns:
        A dict with ``profile``, ``orders`` (with invoice lines in ``lines``),
        ``carts`` (with ``qty_total`` and ``money_total``), ``tickets``,
        ``comments`` (latest 50), ``favorites``, ``media``, ``events`` (timeline,
        newest first, at most ``MAX_EVENTS``) and ``cards`` (summary figures).

    Note:
        Tickets are read through ``_base_manager`` so archived tickets are
        included. If the user has no profile, only the user's own events and
        zeroed cards are returned.
    """

    profile = getattr(user, 'profile', None)
    events = _user_events(user)

    data = {
        'profile': profile,
        'orders': [], 'carts': [], 'tickets': [], 'comments': [],
        'favorites': [], 'media': [],
    }
    open_tickets = comments_count = favorites_count = active_items = 0

    if profile is not None:
        events += _profile_events(profile, user)
        events += _order_events(profile, user)
        events += _ticket_events(profile, user)
        events += _comment_events(profile, user)

        data['orders'] = list(
            Order.objects.filter(profile=profile)
            .prefetch_related(Prefetch(
                'invoices',
                queryset=Invoice.objects.select_related('product'),
                to_attr='lines',
            ))
            .order_by('-created_date')
        )

        carts = list(
            Cart.objects.filter(profile=profile)
            .prefetch_related(Prefetch(
                'cart_items', queryset=CartItem.objects.select_related('product'),
            ))
            .order_by('-updated_date')
        )
        for cart in carts:
            items = list(cart.cart_items.all())
            cart.qty_total = sum(i.quantity for i in items)
            cart.money_total = sum(
                i.quantity * (i.price if i.price is not None else i.product.price) for i in items
            )
            if cart.status == 'active':
                active_items = cart.qty_total
        data['carts'] = carts

        data['tickets'] = list(
            Ticket._base_manager.filter(profile=profile)
            .annotate(messages_count=Count('message'))
            .order_by('-created_date')
        )
        open_tickets = sum(1 for t in data['tickets'] if t.status != 'closed')

        data['comments'] = list(profile.comments.select_related('product').order_by('-created_date')[:50])
        comments_count = profile.comments.count()
        data['favorites'] = list(profile.favorites.select_related('product_id').order_by('-created_date'))
        favorites_count = len(data['favorites'])
        data['media'] = list(profile.multimedias.select_related('product').order_by('-created_date'))

    events.sort(key=lambda e: e['date'], reverse=True)
    data['events'] = events[:MAX_EVENTS]

    spent = getattr(user, 'total_spent', None) or 0
    data['cards'] = [
        {'label': 'سفارش‌ها', 'value': getattr(user, 'orders_count', 0)},
        {'label': 'مجموع خرید', 'value': f'{int(spent):,} تومان'},
        {'label': 'تیکت باز', 'value': open_tickets},
        {'label': 'نظرات', 'value': comments_count},
        {'label': 'علاقه‌مندی‌ها', 'value': favorites_count},
        {'label': 'اقلام سبد فعال', 'value': active_items},
    ]
    return data