from django.core.management.base import BaseCommand
from core.models import Profile
from django.utils import timezone
from core.utils import send_alert_via_emailjs

class Command(BaseCommand):
    help = 'Check for missing users and send alerts'

    def handle(self, *args, **options):
        profiles = Profile.objects.filter(alert_sent=False)
        for profile in profiles:
            if profile.is_missing():
                if send_alert_via_emailjs(profile):
                    profile.alert_sent = True
                    profile.save()
                    self.stdout.write(self.style.SUCCESS(f"Alert sent for {profile.user.email}"))
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to send alert for {profile.user.email}"))