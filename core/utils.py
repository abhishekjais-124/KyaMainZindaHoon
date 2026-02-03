import os
import requests
from django.contrib.auth.models import User


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


def send_alert_via_emailjs(profile):
    service_id = os.environ.get('EMAILJS_SERVICE_ID')
    template_id = os.environ.get('EMAILJS_TEMPLATE_ID')
    user_id = os.environ.get('EMAILJS_USER_ID')
    access_token = os.environ.get('EMAILJS_ACCESS_TOKEN')

    if not all([service_id, template_id, user_id, access_token]):
        return False

    partners = profile.get_partners()
    if not partners:
        return False

    user_name = profile.user.get_full_name() or profile.user.username or profile.user.email
    url = f"https://api.emailjs.com/api/v1.0/email/send"
    any_sent = False
    for partner in partners:
        partner_name = partner.user.get_full_name() or partner.user.username or partner.user.email
        message = f"Oye {partner_name}, {user_name} gayab ho gaya hai! Check karo jaldi. Sab changa si? Am I Alive app se alert."
        payload = {
            "service_id": service_id,
            "template_id": template_id,
            "user_id": user_id,
            "accessToken": access_token,
            "template_params": {
                "to_name": partner_name,
                "message": message,
            }
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            any_sent = True
    return any_sent