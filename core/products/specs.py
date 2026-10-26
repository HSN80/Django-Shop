"""Friendly editor for the ``Catalog.specs`` JSON field in the admin.

Specifications are stored as ``{"group title": {"name": "value", ...}, ...}``,
which is the shape the product page template reads. This module replaces the
raw JSON text box with an editor where groups and rows are added and removed
with buttons, and validates what comes back.
"""
import json
from collections import Counter

from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.safestring import mark_safe

MAX_GROUPS = 30
MAX_ROWS = 60
MAX_TITLE = 80
MAX_KEY = 80
MAX_VALUE = 300

LOOSE_GROUP_TITLE = 'مشخصات کلی'


def _text(value):
    return '' if value is None else str(value)


def specs_to_groups(value):
    """Convert stored specs into the list of groups the editor works with.

    Args:
        value: The stored dict, its JSON text, or a list that is already in
            the editor format (for example after a validation error).

    Returns:
        A list like ``[{"title": "...", "rows": [{"key": "...", "value": "..."}]}]``.
        Anything that cannot be understood becomes an empty list. Plain
        ``name: value`` pairs that are not inside a group are collected in a
        group called ``LOOSE_GROUP_TITLE``, so old data is never lost.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return []

    if isinstance(value, list):
        groups = []
        for group in value:
            if not isinstance(group, dict):
                continue
            rows = [
                {'key': _text(row.get('key')), 'value': _text(row.get('value'))}
                for row in (group.get('rows') or []) if isinstance(row, dict)
            ]
            groups.append({'title': _text(group.get('title')), 'rows': rows})
        return groups

    if not isinstance(value, dict):
        return []

    groups, loose = [], []
    for title, rows in value.items():
        if isinstance(rows, dict):
            groups.append({
                'title': _text(title),
                'rows': [{'key': _text(k), 'value': _text(v)} for k, v in rows.items()],
            })
        else:
            loose.append({'key': _text(title), 'value': _text(rows)})
    if loose:
        groups.insert(0, {'title': LOOSE_GROUP_TITLE, 'rows': loose})
    return groups


def groups_to_specs(groups):
    """Validate the editor's groups and convert them to the stored dict.

    Empty rows and groups without any row are dropped.

    Args:
        groups: A list of groups in the editor format.

    Returns:
        A dict ``{"group title": {"name": "value"}}`` in the order of the editor.

    Raises:
        ValidationError: If the structure is wrong, a name or value is missing,
            a group or name is repeated, or a size limit is exceeded.
    """
    if not isinstance(groups, list):
        raise ValidationError('ساختار مشخصات معتبر نیست.')
    if len(groups) > MAX_GROUPS:
        raise ValidationError(f'حداکثر {MAX_GROUPS} گروه مجاز است.')

    specs = {}
    for group in groups:
        if not isinstance(group, dict):
            raise ValidationError('ساختار مشخصات معتبر نیست.')
        title = _text(group.get('title')).strip()
        raw_rows = group.get('rows') or []
        if not isinstance(raw_rows, list) or len(raw_rows) > MAX_ROWS:
            raise ValidationError(f'هر گروه حداکثر {MAX_ROWS} مشخصه دارد.')

        rows = {}
        for row in raw_rows:
            if not isinstance(row, dict):
                raise ValidationError('ساختار مشخصات معتبر نیست.')
            key = _text(row.get('key')).strip()
            value = _text(row.get('value')).strip()
            if not key and not value:
                continue
            if not key:
                raise ValidationError(f'برای مقدار «{value}» نام مشخصه وارد نشده است.')
            if not value:
                raise ValidationError(f'برای مشخصه‌ی «{key}» مقداری وارد نشده است.')
            if len(key) > MAX_KEY or len(value) > MAX_VALUE:
                raise ValidationError(f'مشخصه‌ی «{key[:20]}» بیش از حد طولانی است.')
            if key in rows:
                raise ValidationError(f'مشخصه‌ی «{key}» در گروه «{title}» تکراری است.')
            rows[key] = value

        if not rows:
            continue
        if not title:
            raise ValidationError('یکی از گروه‌ها عنوان ندارد.')
        if len(title) > MAX_TITLE:
            raise ValidationError(f'عنوان گروه «{title[:20]}» بیش از حد طولانی است.')
        if title in specs:
            raise ValidationError(f'گروه «{title}» تکراری است.')
        specs[title] = rows
    return specs


def build_suggestions(exclude_pk=None, sample=200):
    """Collect the group titles and names used by recent products.

    The editor offers these as suggestions, so similar products end up with
    the same wording.

    Args:
        exclude_pk: Primary key of the product being edited, left out of the sample.
        sample: How many of the newest products to look at.

    Returns:
        ``{"groups": [...], "keys": {"group title": [...]}}``, most used first.
    """
    from .models import Catalog

    group_counter = Counter()
    key_counters = {}
    products = Catalog.objects.exclude(pk=exclude_pk).order_by('-id').values_list('specs', flat=True)[:sample]
    for specs in products:
        if not isinstance(specs, dict):
            continue
        for title, rows in specs.items():
            if not isinstance(rows, dict):
                continue
            group_counter[title] += 1
            key_counters.setdefault(title, Counter()).update(rows.keys())

    return {
        'groups': [title for title, _ in group_counter.most_common(30)],
        'keys': {
            title: [key for key, _ in counter.most_common(30)]
            for title, counter in key_counters.items()
        },
    }


ASSETS = r'''
<style>
.specs-editor { flex: 1; max-width: 900px; }
.specs-editor .specs-help { margin: 0 0 8px; color: var(--body-quiet-color); font-size: 12px; }
.specs-editor .specs-group { border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; margin-bottom: 10px; background: var(--darkened-bg); }
.specs-editor .specs-head, .specs-editor .specs-row { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.specs-editor input[type="text"] { flex: 1; min-width: 0; width: 100%; box-sizing: border-box; }
.specs-editor .specs-title { font-weight: 700; }
.specs-editor .specs-btn { cursor: pointer; padding: 4px 10px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--body-bg); color: var(--body-fg); }
.specs-editor .specs-danger { color: var(--error-fg); }
.specs-editor .specs-empty { padding: 10px; color: var(--body-quiet-color); }
</style>
<script>
(function () {
  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (name) { node.setAttribute(name, attrs[name]); });
    }
    if (text) { node.textContent = text; }
    return node;
  }

  function initEditor(root) {
    if (root.getAttribute('data-ready')) { return; }
    root.setAttribute('data-ready', '1');

    var input = root.querySelector('.specs-value');
    var board = root.querySelector('.specs-board');
    var empty = root.querySelector('.specs-empty');
    var addGroupButton = root.querySelector('.specs-add-group');
    var suggestions = JSON.parse(root.getAttribute('data-suggestions'));
    var limits = JSON.parse(root.getAttribute('data-limits'));
    var initial = JSON.parse(root.getAttribute('data-initial'));
    var counter = 0;

    var groupList = el('datalist', {id: root.id + '-groups'});
    fillList(groupList, suggestions.groups || []);
    root.appendChild(groupList);

    function fillList(list, names) {
      while (list.firstChild) { list.removeChild(list.firstChild); }
      names.forEach(function (name) {
        var option = el('option');
        option.value = name;
        list.appendChild(option);
      });
    }

    function sync() {
      var data = [];
      board.querySelectorAll('.specs-group').forEach(function (group) {
        var rows = [];
        group.querySelectorAll('.specs-row').forEach(function (row) {
          var fields = row.querySelectorAll('input');
          rows.push({key: fields[0].value, value: fields[1].value});
        });
        data.push({title: group.querySelector('.specs-title').value, rows: rows});
      });
      input.value = JSON.stringify(data);
      empty.hidden = data.length > 0;
    }

    function onEnter(event) {
      if (event.key !== 'Enter') { return; }
      event.preventDefault();  // Enter must not submit the whole admin form
      var fields = Array.prototype.slice.call(board.querySelectorAll('input'));
      var index = fields.indexOf(event.target);
      if (index < fields.length - 1) {
        fields[index + 1].focus();
      } else if (board.lastElementChild) {
        board.lastElementChild.querySelector('.specs-add-row').click();
      }
    }

    function addRow(rowsBox, keyListId, key, value) {
      var row = el('div', {'class': 'specs-row'});
      var keyInput = el('input', {
        type: 'text', dir: 'auto', list: keyListId, maxlength: limits.key,
        placeholder: 'نام مشخصه، مثلاً «طول»'
      });
      var valueInput = el('input', {
        type: 'text', dir: 'auto', maxlength: limits.value,
        placeholder: 'مقدار، مثلاً «۱۲ سانتی‌متر»'
      });
      keyInput.value = key || '';
      valueInput.value = value || '';
      var remove = el('button', {type: 'button', 'class': 'specs-btn specs-danger', title: 'حذف مشخصه'}, '✕');
      remove.addEventListener('click', function () { rowsBox.removeChild(row); sync(); });
      [keyInput, valueInput].forEach(function (field) {
        field.addEventListener('input', sync);
        field.addEventListener('keydown', onEnter);
      });
      row.appendChild(keyInput);
      row.appendChild(valueInput);
      row.appendChild(remove);
      rowsBox.appendChild(row);
      return keyInput;
    }

    function addGroup(title, rows) {
      counter += 1;
      var group = el('div', {'class': 'specs-group'});
      var keyList = el('datalist', {id: root.id + '-keys-' + counter});
      var head = el('div', {'class': 'specs-head'});
      var titleInput = el('input', {
        type: 'text', 'class': 'specs-title', dir: 'auto', list: groupList.id, maxlength: limits.title,
        placeholder: 'عنوان گروه، مثلاً «ابعاد»'
      });
      titleInput.value = title || '';
      var removeGroup = el('button', {type: 'button', 'class': 'specs-btn specs-danger'}, 'حذف گروه');
      var rowsBox = el('div', {'class': 'specs-rows'});
      var addRowButton = el('button', {type: 'button', 'class': 'specs-btn specs-add-row'}, '+ افزودن مشخصه');

      function refreshKeys() {
        fillList(keyList, (suggestions.keys || {})[titleInput.value.trim()] || []);
      }

      titleInput.addEventListener('input', function () { refreshKeys(); sync(); });
      titleInput.addEventListener('keydown', onEnter);
      removeGroup.addEventListener('click', function () {
        var filled = Array.prototype.some.call(group.querySelectorAll('.specs-row'), function (row) {
          var fields = row.querySelectorAll('input');
          return fields[0].value || fields[1].value;
        });
        if (!filled || window.confirm('این گروه با همه‌ی مشخصاتش حذف شود؟')) {
          board.removeChild(group);
          sync();
        }
      });
      addRowButton.addEventListener('click', function () {
        addRow(rowsBox, keyList.id, '', '').focus();
        sync();
      });

      (rows || []).forEach(function (row) { addRow(rowsBox, keyList.id, row.key, row.value); });
      refreshKeys();

      head.appendChild(titleInput);
      head.appendChild(removeGroup);
      group.appendChild(keyList);
      group.appendChild(head);
      group.appendChild(rowsBox);
      group.appendChild(addRowButton);
      board.appendChild(group);
      return group;
    }

    addGroupButton.addEventListener('click', function () {
      var group = addGroup('', [{key: '', value: ''}]);
      group.querySelector('.specs-title').focus();
      sync();
    });

    initial.forEach(function (group) { addGroup(group.title, group.rows); });
    sync();

    var form = root.closest('form');
    if (form) { form.addEventListener('submit', sync); }
  }

  function initAll() {
    Array.prototype.forEach.call(document.querySelectorAll('.specs-editor'), initEditor);
  }

  initAll();
  document.addEventListener('DOMContentLoaded', initAll);
})();
</script>
'''


class SpecsWidget(forms.Widget):
    """Editor widget for product specifications.

    Renders groups of name/value rows that can be added, removed and edited
    with buttons. The state is kept in a hidden input as JSON in the editor
    format (see ``specs_to_groups``).

    Attributes:
        suggestions: Output of ``build_suggestions`` (optional); offered as
            auto-complete for group titles and names.
    """

    suggestions = None

    def render(self, name, value, attrs=None, renderer=None):
        groups = specs_to_groups(value)
        suggestions = self.suggestions or {'groups': [], 'keys': {}}
        limits = {'title': MAX_TITLE, 'key': MAX_KEY, 'value': MAX_VALUE}
        markup = format_html(
            '<div class="specs-editor" id="{id}" data-initial="{initial}" '
            'data-suggestions="{suggestions}" data-limits="{limits}">'
            '<p class="specs-help">مشخصات به‌صورت گروه‌بندی‌شده در صفحه‌ی محصول نمایش داده می‌شود؛ '
            'مثلاً گروه «ابعاد» با مشخصه‌های «طول» و «عرض».</p>'
            '<input type="hidden" class="specs-value" name="{name}" value="{initial}">'
            '<div class="specs-board"></div>'
            '<div class="specs-empty">هنوز مشخصه‌ای اضافه نشده است.</div>'
            '<button type="button" class="specs-btn specs-add-group">+ افزودن گروه</button>'
            '</div>',
            id=(attrs or {}).get('id') or f'id_{name}',
            name=name,
            initial=json.dumps(groups, ensure_ascii=False),
            suggestions=json.dumps(suggestions, ensure_ascii=False),
            limits=json.dumps(limits),
        )
        return mark_safe(f'{markup}{ASSETS}')


class SpecsField(forms.JSONField):
    """Form field that edits product specifications with ``SpecsWidget``.

    The submitted editor data is validated and converted to the stored
    ``{"group": {"name": "value"}}`` dict. An empty editor gives ``{}``.
    """

    widget = SpecsWidget

    def __init__(self, **kwargs):
        kwargs.setdefault('required', False)
        super().__init__(**kwargs)

    def to_python(self, value):
        data = super().to_python(value)
        if data in (None, '', [], {}):
            return {}
        return groups_to_specs(data)

    def has_changed(self, initial, data):
        try:
            new = self.to_python(data)
        except ValidationError:
            return True
        return (initial or {}) != new