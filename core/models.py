from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q


import random
import string
def generate_invite_code():
    # 5 chars, lowercase letters and digits, unique
    chars = string.ascii_lowercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=5))
        if not Profile.objects.filter(invite_code=code).exists():
            return code

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_check_in = models.DateTimeField(default=timezone.now)
    alert_sent = models.BooleanField(default=False)
    invite_code = models.CharField(max_length=5, unique=True, null=False, blank=False, editable=False)
    share_location_with_friends = models.BooleanField(default=False)
    snooze_enabled = models.BooleanField(default=False)
    last_latitude = models.FloatField(null=True, blank=True)
    last_longitude = models.FloatField(null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)
    last_city = models.CharField(max_length=120, null=True, blank=True)
    last_state = models.CharField(max_length=120, null=True, blank=True)

    def get_partner(self):
        """Return first partner for backward compatibility."""
        partners = self.get_partners()
        return partners[0] if partners else None

    def get_partners(self):
        """Return all active partner profiles (friends), excluding self."""
        mappings = UserPartnerMappings.objects.filter(user=self, is_active=True)
        return [m.partner for m in mappings]

    def is_partner_with(self, other_profile):
        """True if this profile has an active link with other_profile."""
        if other_profile is None or other_profile == self:
            return False
        return UserPartnerMappings.objects.filter(
            user=self, partner=other_profile, is_active=True
        ).exists()

    def __str__(self):
        partners = self.get_partners()
        return f"{self.user.email} - Partners: {', '.join(p.user.email for p in partners) or 'None'}"

    def is_missing(self):
        return timezone.now() - self.last_check_in > timezone.timedelta(hours=48)

    def is_warning(self):
        delta = timezone.now() - self.last_check_in
        return timezone.timedelta(hours=32) < delta <= timezone.timedelta(hours=48)

class UserPartnerMappings(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='mappings_as_user')
    partner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='mappings_as_partner')
    is_active = models.BooleanField(default=True)
    is_emergency = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.user.email} <-> {self.partner.user.email}"


class SOSAlert(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        RESOLVED = 'resolved', 'Resolved'

    from_user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sos_sent')
    to_user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sos_received')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='sos_resolved'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SOS {self.from_user.user.email} → {self.to_user.user.email} ({self.status})"


class SOSResolvedNotification(models.Model):
    """When an emergency contact resolves an SOS, the triggerer gets this so we can show a popup."""
    triggerer = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name='sos_resolved_notifications'
    )
    resolved_by = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name='sos_resolved_notifications_given'
    )
    created_at = models.DateTimeField(default=timezone.now)
    seen = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
