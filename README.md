# Am I Alive

A Django web app for a "Dead Man's Switch" where pairs of users check in to ensure each other's safety.

## Features

- User authentication via Google SSO using django-allauth
- Profile model with partner relationships
- Mobile-first UI with Tailwind CSS and dark mode
- Email notifications via EmailJS REST API
- Management command to check for missing users

## Setup

1. Create virtual environment: `python3 -m venv venv`
2. Activate: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Set local env vars (at minimum `DEBUG=True`; optionally `SECRET_KEY`)
5. Run migrations: `python manage.py migrate`
6. Create superuser: `python manage.py createsuperuser`
7. Run server: `python manage.py runserver`

## Environment Variables

Set the following in your environment:

- `SECRET_KEY` (required in production; generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `DEBUG` (`True` for local development; leave unset or `False` in production)
- `FORCE_SCRIPT_NAME` (optional; set only when the app is mounted under a subdirectory reverse proxy, e.g. `FORCE_SCRIPT_NAME=/zinda` for aj124.com. Leave unset on Render at root.)
- `EMAILJS_SERVICE_ID`
- `EMAILJS_TEMPLATE_ID`
- `EMAILJS_USER_ID`
- `EMAILJS_ACCESS_TOKEN`

EmailJS template must use dynamic To Email `{{to_email}}` (also uses `{{to_name}}`, `{{message}}`, `{{subject}}`). Without `{{to_email}}` in the template, partner/SOS emails will not reach recipients.
- `GOOGLE_CLIENT_ID` (for allauth)
- `GOOGLE_CLIENT_SECRET`
- `DATABASE_PATH` (optional; set on server to a persistent path, e.g. `/data/db.sqlite3`, so sessions, connections, and check-ins survive deploys)


## Deployment

1. Ensure you have a `.env` file with your environment variables (see above). In production set a strong `SECRET_KEY` and do **not** set `DEBUG=True`.
2. **Persist the database** so connections, check-ins, and logins survive deploys:
   - Set `DATABASE_PATH` to a path on a **persistent disk** (e.g. `DATABASE_PATH=/data/db.sqlite3`).
   - On Render: add a Persistent Disk, mount it (e.g. at `/data`), then set env var `DATABASE_PATH=/data/db.sqlite3`.
   - On Railway or similar: use a persistent volume path and set `DATABASE_PATH` to a file inside it.
   - If you don't set `DATABASE_PATH`, the app uses `db.sqlite3` in the project directory, which is usually recreated on each deploy and causes data loss.
4. Static files are served using WhiteNoise (no need for a separate static server).
5. For production, use Gunicorn:
   
	```sh
	gunicorn kya_main_zinda_hoon.wsgi:application
	```

6. A `Procfile` is included for platforms like Heroku/Render:
   
	```
	web: gunicorn kya_main_zinda_hoon.wsgi:application
	```

7. For subdirectory hosting (e.g. `https://aj124.com/zinda/`), set `FORCE_SCRIPT_NAME=/zinda`. Leave it unset when the app is served at the domain root (e.g. Render). App routes remain under `/KyaMainZindaHoon/`; `{% url %}` and named login redirects include the script prefix automatically.

## Management Command

Run `python manage.py check_heartbeats` to check for missing users and send alerts.