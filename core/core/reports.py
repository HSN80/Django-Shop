from datetime import datetime, time, timedelta
from urllib.parse import urlencode
from django.urls import reverse
from django.utils import timezone
from accounts.models import Profile, User
from carts.models import Cart
from multimedia.models import Media
from orders.models import Invoice, Order
from products.models import Catalog, Category, Comment, Discount, Image
from tickets.models import Message, Ticket
from userfav.models import Favorites

"""
Data builders for the admin reports.

``build_activity`` produces the activity timeline (what changed, when and by
whom, across all sections) and ``build_state`` reconstructs how a section
looked on a chosen day. Both read the ``simple_history`` tables, so they only
know about changes made after history logging was installed.
"""


"""
Fields ignored when comparing history records.

These change on every save by themselves (timestamps, last login) or must
never be shown (password hash), so they do not count as real edits.
"""
NOISE_FIELDS = {'updated_date', 'created_date', 'last_login', 'password'}

"""Labels for the ``simple_history`` record types: created, changed, deleted."""
KINDS = {'+': 'ثبت', '~': 'ویرایش', '-': 'حذف'}

"""
Paging of the activity report: the default number of events shown, how many
more each "show more" click adds, and the hard upper limit."""
DEFAULT_LIMIT, STEP, MAX_LIMIT = 100, 100, 500

"""
Models included in the activity report, grouped by section.

Each section is ``(key, title, models)``, and each model entry is
``(model, label, label_function)``, where ``label_function`` builds a short
name for an object from its history record without extra queries. Every model
listed here must have a ``history`` manager.
"""
ACTIVITY_SECTIONS = [

    ('users', 'کاربران', [
        (User, 'کاربر', lambda r: r.username),
        (Profile, 'پروفایل', lambda r: f'#{r.id}'),
    ]),
    ('catalog', 'محصولات', [
        (Catalog, 'محصول', lambda r: r.title),
        (Category, 'دسته‌بندی', lambda r: r.title),
        (Discount, 'تخفیف', lambda r: r.title),
        (Image, 'تصویر', lambda r: f'#{r.id}'),
        (Comment, 'نظر', lambda r: f'#{r.id}'),
    ]),
    ('sales', 'فروش', [
        (Order, 'سفارش', lambda r: f'#{r.id} {r.first_name} {r.last_name}'),
        (Invoice, 'فاکتور', lambda r: f'#{r.id}'),
        (Cart, 'سبد', lambda r: f'#{r.id}'),
    ]),
    ('support', 'پشتیبانی', [
        (Ticket, 'تیکت', lambda r: r.subject),
        (Message, 'پیام', lambda r: f'#{r.id}'),
    ]),
    ('engagement', 'محتوا و تعامل', [
        (Favorites, 'علاقه‌مندی', lambda r: f'#{r.id}'),
        (Media, 'رسانه', lambda r: f'#{r.id}'),
    ]),
]


def _day_start(day):

    """Return midnight at the start of ``day`` as a timezone-aware datetime."""

    return timezone.make_aware(datetime.combine(day, time.min))


def _parse_date(value):

    """
    Parse a ``YYYY-MM-DD`` string into a date.

    Returns:
        The date, or ``None`` if the value is missing or malformed.
    """

    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _fmt(field, value):
    
    """
    Format a field value for display in the activity report.

    Empty values become an em dash, booleans become yes/no, fields with choices
    show their label, and everything else is converted to text and cut to 40
    characters.
    
    Args:
        field: The model field the value belongs to.
        value: The raw value.
    
    Returns:
        The display string.
    """

    if value is None or value == '':
        return '—'
    if isinstance(value, bool):
        return 'بله' if value else 'خیر'
    if field.choices:
        value = dict(field.flatchoices).get(value, value)
    return str(value)[:40]


def _diff(rec, prev):

    """
    List the fields that differ between two history records of one object.

    Args:
        rec: The newer history record.
        prev: The previous history record of the same object.

    Returns:
        A list of ``(field_label, old_value, new_value)`` tuples with values
        formatted for display. History bookkeeping fields and ``NOISE_FIELDS``
        are skipped.
    """

    changes = []
    for field in rec._meta.concrete_fields:
        if field.name.startswith('history_') or field.name in NOISE_FIELDS:
            continue
        old, new = getattr(prev, field.attname), getattr(rec, field.attname)
        if old != new:
            changes.append((str(field.verbose_name), _fmt(field, old), _fmt(field, new)))
    return changes


def build_activity(params):

    """
    Build the activity timeline from the history of all tracked models.

    Reads the filters from ``params`` (usually ``request.GET``): ``section``,
    ``action`` (``+``, ``~`` or ``-``), ``by`` (``staff``, ``users`` or
    ``system``), ``since`` and ``until`` (inclusive ``YYYY-MM-DD`` dates) and
    ``limit``. Missing or invalid values fall back to "all" and the default
    limit.

    Args:
        params: A dict-like object holding the filter values.

    Returns:
        A dict for the template with ``events`` (newest first; each has date,
        section, kind, object, link, author, reason and field changes),
        ``filters``, ``more_url`` (empty when there is nothing more to show) and
        the options of the filter drop-downs.

    Note:
        Edits that changed no visible field (for example a save that only
        updated ``last_login``) are dropped, so fewer events than the limit may
        be returned. Each edit costs one extra query to fetch the previous
        version. Links are not added for deleted objects.
    """

    section = params.get('section', 'all')
    action = params.get('action', 'all')
    by = params.get('by', 'all')
    since = _parse_date(params.get('since'))
    until = _parse_date(params.get('until'))
    try:
        limit = min(max(int(params.get('limit', DEFAULT_LIMIT)), 1), MAX_LIMIT)
    except ValueError:
        limit = DEFAULT_LIMIT

    rows = []
    for key, section_label, models in ACTIVITY_SECTIONS:
        if section not in ('all', key):
            continue
        for model, model_label, label_fn in models:
            qs = model.history.select_related('history_user').order_by('-history_date', '-history_id')
            if since:
                qs = qs.filter(history_date__gte=_day_start(since))
            if until:
                qs = qs.filter(history_date__lt=_day_start(until + timedelta(days=1)))
            if action in KINDS:
                qs = qs.filter(history_type=action)
            if by == 'staff':
                qs = qs.filter(history_user__is_staff=True)
            elif by == 'users':
                qs = qs.filter(history_user__is_staff=False)
            elif by == 'system':
                qs = qs.filter(history_user__isnull=True)
            rows.extend((rec, model, section_label, model_label, label_fn) for rec in qs[:limit])

    rows.sort(key=lambda r: r[0].history_date, reverse=True)
    has_more = len(rows) > limit
    rows = rows[:limit]

    events = []
    for rec, model, section_label, model_label, label_fn in rows:
        kind = rec.history_type
        changes = []
        if kind == '~':
            prev = (
                type(rec)._default_manager
                .filter(id=rec.id, history_id__lt=rec.history_id)
                .order_by('-history_id').first()
            )
            changes = _diff(rec, prev) if prev else []
            if not changes:
                continue

        actor = rec.history_user
        if actor is None:
            by_text = 'سیستم'
        else:
            by_text = actor.username + (' (ادمین)' if actor.is_staff else '')

        url = ''
        if kind != '-':
            opts = model._meta
            url = reverse(f'admin:{opts.app_label}_{opts.model_name}_change', args=[rec.id])

        events.append({
            'date': rec.history_date,
            'section': section_label,
            'kind': KINDS[kind],
            'kind_key': kind,
            'object': f'{model_label} «{label_fn(rec)}»',
            'url': url,
            'by': by_text,
            'reason': rec.history_change_reason or '',
            'changes': changes,
        })

    filters = {
        'section': section, 'action': action, 'by': by,
        'since': params.get('since', ''), 'until': params.get('until', ''),
    }
    more_url = ''
    if has_more and limit < MAX_LIMIT:
        more_url = '?' + urlencode({**filters, 'limit': min(limit + STEP, MAX_LIMIT)})

    return {
        'events': events,
        'filters': filters,
        'more_url': more_url,
        'section_options': [('all', 'همه‌ی بخش‌ها')] + [(k, label) for k, label, _ in ACTIVITY_SECTIONS],
        'action_options': [('all', 'همه‌ی عملیات'), ('+', 'ثبت'), ('~', 'ویرایش'), ('-', 'حذف')],
        'by_options': [
            ('all', 'همه'), ('staff', 'فقط ادمین‌ها'),
            ('users', 'فقط کاربران'), ('system', 'سیستم'),
        ],
    }


def _num(value):
    
    """Format a number with thousands separators; ``None`` becomes an em dash."""

    return '—' if value is None else f'{int(value):,}'


def _yn(value):
    
    """Return the yes/no label for a boolean."""
    
    return 'بله' if value else 'خیر'


"""
Sections available in the state-at-date report.

Maps a section key to ``(title, model, columns)``, where ``columns`` is a
list of ``(header, function)`` pairs and each function turns an object, as it
was on the chosen day, into the cell text.
"""
STATE_SECTIONS = {

    'products': ('محصولات', Catalog, [
        ('محصول', lambda o: o.title),
        ('قیمت', lambda o: _num(o.price)),
        ('تخفیف', lambda o: '—' if o.discount is None else o.discount),
        ('موجودی', lambda o: o.stock),
        ('وضعیت', lambda o: o.get_status_display()),
    ]),
    'categories': ('دسته‌بندی‌ها', Category, [
        ('عنوان', lambda o: o.title),
        ('اسلاگ', lambda o: o.slug),
    ]),
    'discounts': ('تخفیف‌ها', Discount, [
        ('عنوان', lambda o: o.title),
        ('درصد', lambda o: o.percent),
        ('فعال', lambda o: _yn(o.is_active)),
    ]),
    'orders': ('سفارش‌ها', Order, [
        ('سفارش', lambda o: f'#{o.id}'),
        ('مشتری', lambda o: f'{o.first_name} {o.last_name}'),
        ('مبلغ', lambda o: _num(o.price)),
        ('وضعیت', lambda o: o.get_status_display()),
        ('کد رهگیری', lambda o: o.tracking_code or '—'),
    ]),
    'users': ('کاربران', User, [
        ('نام کاربری', lambda o: o.username),
        ('تلفن', lambda o: str(o.phone)),
        ('فعال', lambda o: _yn(o.is_active)),
        ('تأیید شده', lambda o: _yn(o.is_verified)),
    ]),
}


def build_state(params):

    """
    Reconstruct how a section looked at the end of a chosen day.

    Uses ``simple_history``'s ``as_of`` to rebuild every object as it was at that
    time. Objects deleted by then are left out.

    Args:
        params: A dict-like object (usually ``request.GET``) with ``section``
            (a key of ``STATE_SECTIONS``, ``products`` by default) and ``date``
            (``YYYY-MM-DD``, today by default).

    Returns:
        A dict for the template with the section and day, the table ``headers``
        and ``rows``, the object ``count``, a ``summary`` line (total of paid
        orders for the orders section), ``first_record`` (when history started)
        and ``before_logging`` (``True`` if the chosen day is before that).

    Note:
        The ``system`` user is hidden from the users section. All objects of the
        section are loaded into memory, which is fine for a small shop but
        should be paginated if the tables grow large.
    """

    key = params.get('section')
    if key not in STATE_SECTIONS:
        key = 'products'
    label, model, columns = STATE_SECTIONS[key]

    day = _parse_date(params.get('date')) or timezone.localdate()
    at = _day_start(day + timedelta(days=1))

    objs = list(model.history.as_of(at))
    if key == 'users':
        objs = [o for o in objs if o.username != 'system']
    objs.sort(key=lambda o: o.pk)

    first = model.history.order_by('history_date').values_list('history_date', flat=True).first()
    summary = ''
    if key == 'orders':
        paid = sum(o.price for o in objs if o.status in Order.PAID_STATUSES)
        summary = f'جمع سفارش‌های پرداخت‌شده: {paid:,} تومان'

    return {
        'state_options': [(k, v[0]) for k, v in STATE_SECTIONS.items()],
        'section': key,
        'section_label': label,
        'day': day.isoformat(),
        'headers': [title for title, _ in columns],
        'rows': [[fn(o) for _, fn in columns] for o in objs],
        'count': len(objs),
        'summary': summary,
        'first_record': first,
        'before_logging': first is not None and at < first,
    }