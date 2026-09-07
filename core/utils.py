import os
import logging
import requests
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections

logger = logging.getLogger(__name__)

EMAILJS_SEND_URL = 'https://api.emailjs.com/api/v1.0/email/send'
_background_executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix='kmzh-background',
)


def _run_with_fresh_db_connection(callback, *args):
    close_old_connections()
    try:
        return callback(*args)
    finally:
        close_old_connections()


def _log_background_failure(future):
    try:
        future.result()
    except Exception:
        logger.exception('Background task failed')


def run_in_background(callback, *args):
    """Run non-response work without blocking the current request."""
    future = _background_executor.submit(
        _run_with_fresh_db_connection,
        callback,
        *args,
    )
    future.add_done_callback(_log_background_failure)
    return future


def reverse_geocode(lat, lng):
    """Return (city, state) for given lat/lng using Nominatim. Returns (None, None) on failure."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        r = requests.get(url, headers={"User-Agent": "AmIOkApp/1.0"}, timeout=5)
        if r.status_code != 200:
            return None, None
        data = r.json()
        address = data.get("address") or {}
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
        )
        state = address.get("state") or address.get("region")
        return (city[:120] if city else None), (state[:120] if state else None)
    except Exception:
        return None, None


def update_profile_location_name(profile_id, lat, lng):
    """Reverse-geocode a saved location without delaying the response."""
    from .models import Profile

    city, state = reverse_geocode(lat, lng)
    if not city and not state:
        return
    Profile.objects.filter(
        pk=profile_id,
        last_latitude=lat,
        last_longitude=lng,
    ).update(last_city=city, last_state=state)


def send_sos_emails_for_ids(profile_id, recipient_ids):
    """Load SOS recipients in a worker and send secondary email alerts."""
    from .models import Profile

    profile = Profile.objects.select_related('user').get(pk=profile_id)
    recipients = list(
        Profile.objects
        .filter(pk__in=recipient_ids)
        .select_related('user')
    )
    send_sos_via_emailjs(profile, recipients)


def _emailjs_credentials():
    service_id = os.environ.get('EMAILJS_SERVICE_ID')
    template_id = os.environ.get('EMAILJS_TEMPLATE_ID')
    user_id = os.environ.get('EMAILJS_USER_ID')
    access_token = os.environ.get('EMAILJS_ACCESS_TOKEN')
    if not all([service_id, template_id, user_id, access_token]):
        return None
    return {
        'service_id': service_id,
        'template_id': template_id,
        'user_id': user_id,
        'accessToken': access_token,
    }


def _display_name(user):
    return user.get_full_name() or user.username or user.email or 'User'


def _location_snippet(profile):
    """Short location text when the user has shared coordinates."""
    if profile.last_latitude is None or profile.last_longitude is None:
        return ''
    place = ', '.join(p for p in (profile.last_city, profile.last_state) if p)
    coords = f"{profile.last_latitude}, {profile.last_longitude}"
    if place:
        return f" Last known location: {place} ({coords})."
    return f" Last known location: {coords}."


def send_emailjs(to_email, to_name, message, subject=None):
    """
    Send one email via EmailJS.

    The EmailJS template "To Email" field must be set to {{to_email}}
    (and typically {{to_name}} / {{message}} / {{subject}} in the body/subject).
    """
    creds = _emailjs_credentials()
    if not creds or not to_email:
        return False

    template_params = {
        'to_email': to_email,
        'email': to_email,  # common alternate template variable
        'to_name': to_name or to_email,
        'message': message,
        'subject': subject or 'Am I Alive alert',
    }
    payload = {**creds, 'template_params': template_params}
    try:
        response = requests.post(EMAILJS_SEND_URL, json=payload, timeout=15)
        if response.status_code == 200:
            return True
        logger.warning(
            'EmailJS send failed (%s): %s',
            response.status_code,
            response.text[:300],
        )
    except requests.RequestException:
        logger.exception('EmailJS request error for %s', to_email)
    return False


def send_heartbeat_alert(profile, partner):
    """Notify one connection that this user crossed their heartbeat limit."""
    to_email = (partner.user.email or '').strip()
    if not to_email:
        logger.warning(
            'Skipping missing-person alert: partner %s has no email',
            partner.user_id,
        )
        return False

    user_name = _display_name(profile.user)
    partner_name = _display_name(partner.user)
    message = (
        f"Oye {partner_name}, {user_name} gayab ho gaya hai! "
        f"Check karo jaldi. Sab changa si? Am I Alive app se alert."
    )
    return send_emailjs(
        to_email=to_email,
        to_name=partner_name,
        message=message,
        subject=f'Am I Alive: {user_name} may be missing',
    )


def send_alert_via_emailjs(profile):
    """Notify all partners that this user is missing (backward-compatible helper)."""
    any_sent = False
    for partner in profile.get_partners():
        if send_heartbeat_alert(profile, partner):
            any_sent = True
    return any_sent


def send_sos_via_emailjs(profile, recipients):
    """
    Notify emergency contacts about an SOS.

    recipients: iterable of Profile objects (emergency contacts).
    """
    user_name = _display_name(profile.user)
    location = ''
    if profile.share_location_in_sos:
        location = _location_snippet(profile)

    any_sent = False
    for partner in recipients:
        to_email = (partner.user.email or '').strip()
        if not to_email:
            logger.warning(
                'Skipping SOS email: contact %s has no email',
                partner.user_id,
            )
            continue
        partner_name = _display_name(partner.user)
        message = (
            f"EMERGENCY SOS: {user_name} triggered an SOS and listed you as an "
            f"emergency contact. Check on them immediately in the Am I Alive app."
            f"{location}"
        )
        if send_emailjs(
            to_email=to_email,
            to_name=partner_name,
            message=message,
            subject=f'Am I Alive SOS: {user_name} needs help',
        ):
            any_sent = True
    return any_sent
