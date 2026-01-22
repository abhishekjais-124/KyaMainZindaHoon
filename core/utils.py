import os
import requests
from django.contrib.auth.models import User

def send_alert_via_emailjs(profile):
    service_id = os.environ.get('EMAILJS_SERVICE_ID')
    template_id = os.environ.get('EMAILJS_TEMPLATE_ID')
    user_id = os.environ.get('EMAILJS_USER_ID')
    access_token = os.environ.get('EMAILJS_ACCESS_TOKEN')

    if not all([service_id, template_id, user_id, access_token]):
        return False

    partner = profile.get_partner()
    if not partner:
        return False

    user_name = profile.user.get_full_name() or profile.user.email
    partner_name = partner.user.get_full_name() or partner.user.email

    message = f"Oye {partner_name}, {user_name} gayab ho gaya hai! Check karo jaldi. Sab changa si? Main Zinda Hoon app se alert."

    url = f"https://api.emailjs.com/api/v1.0/email/send"
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
    return response.status_code == 200