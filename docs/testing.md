# Testing

Run everything:

```bash
python manage.py test
```

Run one group or one test:

```bash
python manage.py test core.tests.DossierTests
python manage.py test core.tests.DossierTests.test_ban_blocks_login_and_is_recorded
```

Current result: 70 tests, all passing.

## Layout

All tests live in `core/tests.py` and share a base class:

| Helper | Purpose |
|---|---|
| `BaseCase` | An admin, two customers, a category and a product; logs the admin in |
| `make_user`, `make_product`, `make_order`, `profile_of` | Small factories |
| `FAST_HASH` | Uses a fast password hasher so tests stay quick |

## What is covered

| Group | Covers |
|---|---|
| `HistoryTests` | Creates, changes and deletes are recorded; admin actions store author and reason; secret fields are never copied |
| `AdminPagesTests` | Every admin list and change page loads; search works; the menu is grouped |
| `CartAdminTests` | Cart totals and the abandoned-carts card |
| `DashboardTests` | Sales count only paid orders, the 30-day window, pending tickets, the hidden `system` user, low stock, superuser-only dashboard |
| `DossierTests` | Ban and unban (a banned user cannot log in), verification, protections, the page and its timeline, 404 for `system`, staff-only access |
| `OrderActionTests`, `TicketAdminTests` | The "sent" and "arrived" rules, comment moderation, closed tickets stay visible, bulk delete disabled, close and reopen |
| `ReportsTests` | Activity feed values and filters, noise filtering, superuser-only access, state at a date (also back in time, and for deleted objects) |
| `MediaSignalTests` | Short, long and unreadable videos, a media without a video |
| `SpecsEditorTests` | Specification validation, escaping, suggestions, the editor on the product page |
| `PaymentTests`, `CheckoutTests` | The checkout and the whole payment flow |
| `CategoryPathTests`, `MigrationTests` | Category URL paths, and that no migration is missing |

## How outside services are tested

- **Zibal** is replaced by a fake `requests.post`, so tests never touch the network.
- **ffmpeg** is replaced by a fake reader that returns a duration, and uploaded files go to a temporary folder.

## Good to know

- `DEBUG_TOOLBAR_CONFIG['IS_RUNNING_TESTS'] = False` is needed because Django sets `DEBUG` to `False` during tests, and the toolbar refuses to run.
- A failing `history_user` assertion usually means `HistoryRequestMiddleware` is missing from `MIDDLEWARE`.
- A failing `MigrationTests` means a model changed without a migration: run `python manage.py makemigrations`.

## Not covered yet

- The public pages (home, category, product) and the comment, favorite and ticket views.
- The accounts flows (registration, verification, password reset).
- Browser behavior: the charts and the specifications editor are checked only by hand.