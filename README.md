<div align="center">

# Django Shop

[English](README.md) · [فارسی](README.fa.md)

![Python](https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/django-5.2-0c4b33?logo=django&logoColor=white)
[![CI](https://github.com/HSN80/Django-Shop/actions/workflows/ci.yml/badge.svg)](https://github.com/USER/REPO/actions/workflows/ci.yml)
![License](https://img.shields.io/github/license/HSN80/Django-Shop)
![Bootstrap](https://img.shields.io/badge/bootstrap-5-7952B3?logo=bootstrap&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

![Storefront](docs/images/storefront.gif)

</div>

## About

Hi, I'm **Hossein Abbasi**, and this is **Django Shop**.

**Django Shop** is a free and open source online shop platform under [MIT LICENSE](LICENSE).
Documents are available in [docs](docs) folder.
Thanks For Your Time.

I tried to implement everything I knew as carefully and thoroughly as I could, and I learned a lot along the way. I hope you enjoy using it as much as I enjoyed building it.

## Screenshots

| Storefront | Category filters | Product page |
|---|---|---|
| ![](docs/images/storefront.png) | ![](docs/images/category.png) | ![](docs/images/product.png) |

| Cart | Checkout and payment | Support tickets |
|---|---|---|
| ![](docs/images/cart.png) | ![](docs/images/checkout.png) | ![](docs/images/tickets.png) |

| Admin dashboard | User dossier | Activity log |
|---|---|---|
| ![](docs/images/dashboard.png) | ![](docs/images/dossier.png) | ![](docs/images/activity.png) |

## Highlights

- **A complete shopping journey:** browse, filter, favorite, add to cart, pay online and track the order.
- **Made for Iran:** prices in Toman, Iranian provinces and cities, the Zibal gateway, and login with a phone number.
- **Customer care built in:** support tickets, moderated comments, email and verification.
- **Easy to run:** Docker setup and compose.
- **Easy to manage:** a dashboard that shows what needs attention today and a full history of every change.

## Features

### Accounts and profiles
- Log in with a phone number, username or email, whichever you prefer
- Registration with email verification
- Password change and password reset with custom pages
- Profiles with address, postal code and a picture; uploads are validated for type and size and converted to WebP
- Reusable access mixins for accounting needs

### Catalog and browsing
- Products with several images, flexible specifications, stock and a draft or published status
- Slugs that work with Persian titles
- Unlimited nested categories with clean URLs that follow the category path
- Category pages with a price-range filter, sorting (cheapest, most expensive, newest), page-size selection, removable filter chips and compact pagination
- Discount campaigns: set one percentage for many products and the discounted prices are calculated automatically; switch a campaign on or off at any time

### Comments and favorites
- Threaded comments with replies
- Moderation: new comments wait for approval and only approved ones are shown
- Favorites that customers can add and remove

### Cart, checkout and payment
- A cart that checks stock and always shows current prices and discounts
- Checkout with Iranian province and city selection, an address pre-filled from the profile, a review step and terms acceptance
- Online payment through [Zibal](https://zibal.ir) (sandbox ready): every payment is verified on the server, repeated callbacks never create duplicate invoices, and a failed payment can be retried
- Orders with statuses and tracking codes; invoice lines keep the price at the time of purchase

### Support tickets
- Tickets sent to a department (finance, technical, account, ...)
- A conversation thread with an automatic acknowledgement reply
- The ticket status follows the conversation, and closed tickets are archived

### Stories and videos
- Video uploads are validated by their real content, not only the file extension
- Clips of 15 seconds or less automatically become stories, and stories can be highlighted

### Admin and shop-owner tools
- **Dashboard:** sales cards, a 30-day sales chart, orders waiting to ship, tickets waiting for a reply and low stock
- **User dossier:** a user's orders with invoice lines, carts, tickets, comments, favorites and media on one page, with ban, unban and verify actions that record a reason
- **Audit trail:** the history of every object, an activity feed showing old and new values, and a "state at date" report
- **Bulk actions** for products, comments, orders and tickets, and a menu grouped by function

### Under the hood
- Docker setup
- Change history for the key models through `django-simple-history`
- Signals, custom managers and validators that keep business rules in one place
- Google-style docstrings across the codebase and an automated test suite

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Django 5.2 |
| Database | SQLite3 |
| Frontend | Django templates, [Shopwise](https://bootstrapmade.com/shopwise-bootstrap-ecommerce-template/) theme, Swiper, GLightbox, Drift |
| Admin charts | Chart.js |
| Payments | Zibal gateway |
| Libraries | django-simple-history, django-phonenumber-field, Pillow, python-magic, imageio-ffmpeg, requests |
| Deployment | Docker |

## Quick start

### With Docker

```bash
git clone https://github.com/HSN80/Django-Shop.git
cd Django-Shop

cp .env.example .env             # then edit the values
docker compose up --build
docker compose exec backend python manage.py createsuperuser
```

### Without Docker

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit the values
cd core
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/> for the shop and <http://127.0.0.1:8000/admin/> for the admin panel.

> Without Docker, `python-magic` needs the `libmagic` system library (on Windows install `python-magic-bin`).

### Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` only in development |
| `ALLOWED_HOSTS` | Comma-separated host names |
| `ZIBAL_MERCHANT` | Zibal merchant code; `zibal` selects the sandbox |
| `SITE_ID` | Id of the Site entry; set its domain in the admin |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` | SMTP server for verification and reset emails |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | SMTP account and sender address |

## Tested

> Continuous integration

Every push and pull request runs the whole suite on GitHub Actions (`.github/workflows/ci.yml`) and checks that the Docker image builds. The badge in the README shows the latest result.

Run it yourself: `python manage.py test`

## Documentation

Detailed documentation lives in [`docs/`](docs/README.md):
[architecture](docs/architecture.md) ·
[data model](docs/data-model.md) ·
[accounts](docs/apps/accounts.md) ·
[products](docs/apps/products.md) ·
[carts](docs/apps/carts.md) ·
[orders](docs/apps/orders.md) ·
[tickets](docs/apps/tickets.md) ·
[favorites](docs/apps/userfav.md) ·
[multimedia](docs/apps/multimedia.md) ·
[payments](docs/payments.md) ·
[admin panel](docs/admin-panel.md) ·
[audit trail](docs/history-audit.md) ·
[testing](docs/testing.md) ·
[deployment](docs/deployment.md)

## Credits

- Storefront theme: [Shopwise](https://bootstrapmade.com/shopwise-bootstrap-ecommerce-template/),
- [Bootstrap](https://getbootstrap.com), [Swiper](https://swiperjs.com), [GLightbox](https://github.com/biati-digital/glightbox), [Drift](https://github.com/imgix/drift), [Chart.js](https://www.chartjs.org)
- Payments: [Zibal](https://zibal.ir)

## License

MIT. See [LICENSE](LICENSE).

## Author

**Hossein Abbasi** 