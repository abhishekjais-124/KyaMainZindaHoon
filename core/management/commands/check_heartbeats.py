from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import UserPartnerMappings
from core.utils import send_heartbeat_alert


class Command(BaseCommand):
    help = 'Check for missing users and send alerts'

    def handle(self, *args, **options):
        # Snooze ("Paused") skips missing-person partner emails.
        mappings = UserPartnerMappings.objects.filter(
            is_active=True,
            heartbeat_alert_sent=False,
            user__snooze_enabled=False,
        ).select_related('user__user', 'partner__user')
        now = timezone.now()
        for mapping in mappings:
            elapsed = now - mapping.user.last_check_in
            if elapsed > timezone.timedelta(hours=mapping.danger_hours):
                if send_heartbeat_alert(mapping.user, mapping.partner):
                    mapping.heartbeat_alert_sent = True
                    mapping.save(update_fields=['heartbeat_alert_sent'])
                    self.stdout.write(self.style.SUCCESS(
                        f"Alert sent for {mapping.user.user.email} "
                        f"to {mapping.partner.user.email}"
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f"Failed to send alert for {mapping.user.user.email} "
                        f"to {mapping.partner.user.email}"
                    ))
