# Deployment

Django Shop can be run with Docker. This page lists what to configure and what to check before and after going live.

## Run with Docker

```bash
cp .env.example .env        # fill in the values
docker compose up --build
docker compose exec backend python manage.py createsuperuser
```

## Environment variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key; never commit it |
| `DEBUG` | `False` in production |
| `ALLOWED_HOSTS` | Your domain names |
| `ZIBAL_MERCHANT` | The real merchant code (`zibal` is the sandbox) |
| `SITE_ID` | The id of the Site entry (usually 1); set its domain to your real domain in the admin |
| `EMAIL_HOST` | Your SMTP or IMAP server e.g: `smtp.gmail.com`|
| `EMAIL_USE_TLS` | If your server can use `TLS` , `True` |
| `EMAIL_PORT` | SMTP or IMAP port |
| `EMAIL_HOST_USER` | Your username |
| `EMAIL_HOST_PASSWORD` | Your password |
| `DEFAULT_FROM_EMAIL` | Your Email domain eg: `admin@example.com` |

## Production settings checklist

- `DEBUG = False`, a real `SECRET_KEY`, `ALLOWED_HOSTS` set.
- `CSRF_TRUSTED_ORIGINS` includes `https://your-domain`.
- Behind a reverse proxy: `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')`, and `USE_X_FORWARDED_HOST = True` if the proxy rewrites the host. Without this, payment callback and verification links are built with `http://`.
- `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` and `SECURE_SSL_REDIRECT` on.
- The **Site** domain (admin, Sites) is your real domain, otherwise verification emails link to `example.com`.
- The Django Debug Toolbar is installed only in development.
- `TIME_ZONE = 'Asia/Tehran'`.
- remember to use a real database for production , the development server uses SQLite3 which is not suitable for production.

Then run:

```bash
python manage.py check --deploy
```

## Static and media files

- Run python manage.py compress --force and python manage.py collectstatic, then serve STATIC_ROOT with the web server.
- Serve `MEDIA_ROOT` (product pictures, profile pictures, videos) from a persistent volume, and include it in backups.

## System requirements

- **libmagic** for video content checks (installed in the image).
- The **ffmpeg** binary shipped with `imageio-ffmpeg` must run on the server. If it cannot, every uploaded video is treated as unreadable and removed, so test one upload and read the logs.
- Internet access from the browser for Chart.js on the admin dashboard.

## First start

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py populate_history --auto     # only when migrating existing data
```

`populate_history` gives existing objects a first history version dated that day (see [audit trail](history-audit.md)).

## Going live with payments

1. Sandbox first: one successful and one failed payment.
2. Put the real merchant code in `ZIBAL_MERCHANT`.
3. Make sure the site is reachable on its public HTTPS address (the gateway sends the customer back to it).
4. Run one real payment of a small amount and check the order, invoice, stock and the `Payment` record in the admin.

## Backups

- Database: back it up regularly (a scheduled pg_dump for PostgreSQL, or a copy of db.sqlite3 when using SQLite)».
- Media: back up the media volume.
- Test a restore at least once.

## After deploying

- Read the application logs after the first video upload and the first payment.
- Walk through: register, verify, browse, add to cart, check out, pay, open a ticket.
- Unpaid orders and pending payments are not cleaned automatically yet 

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| CSRF error on login or forms | Missing `CSRF_TRUSTED_ORIGINS` or the proxy header |
| Emails link to `example.com` | The Site domain was not changed |
| Callback or verification links use `http://` | `SECURE_PROXY_SSL_HEADER` is missing |
| Every video upload disappears | ffmpeg or libmagic does not work on the server; read the logs |
| Dashboard charts are empty | The browser cannot load Chart.js from the CDN |