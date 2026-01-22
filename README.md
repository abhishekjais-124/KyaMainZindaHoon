# Kya Main Zinda Hoon?

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
4. Run migrations: `python manage.py migrate`
5. Create superuser: `python manage.py createsuperuser`
6. Run server: `python manage.py runserver`

## Environment Variables

Set the following in your environment:

- `EMAILJS_SERVICE_ID`
- `EMAILJS_TEMPLATE_ID`
- `EMAILJS_USER_ID`
- `EMAILJS_ACCESS_TOKEN`
- `GOOGLE_CLIENT_ID` (for allauth)
- `GOOGLE_CLIENT_SECRET`

## Deployment

Configured for subdirectory hosting at `/zinda` with `FORCE_SCRIPT_NAME = '/zinda/'`

## Management Command

Run `python manage.py check_heartbeats` to check for missing users and send alerts.