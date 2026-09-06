from django.db import models, transaction
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
    share_location_in_sos = models.BooleanField(default=False)
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

    @transaction.atomic
    def link_with(self, other_profile):
        """
        Create or reactivate a bidirectional friendship.

        Returns (ok, message). Does not create duplicate rows when a soft-deleted
        mapping already exists for (user, partner).
        """
        if other_profile is None:
            return False, "Invalid invite code."
        if other_profile == self:
            return False, "You can't add yourself as a friend."
        if self.is_partner_with(other_profile):
            return False, "You're already friends with this person."

        for user, partner in ((self, other_profile), (other_profile, self)):
            UserPartnerMappings.objects.update_or_create(
                user=user,
                partner=partner,
                defaults={
                    'is_active': True,
                    'is_emergency': False,
                    'heartbeat_alert_sent': False,
                },
            )
        return True, "Friend added!"

    @transaction.atomic
    def unlink_from(self, other_profile):
        """Soft-delete both directions of a friendship and clear emergency flags."""
        if other_profile is None or other_profile == self:
            return False
        UserPartnerMappings.objects.filter(
            Q(user=self, partner=other_profile) | Q(user=other_profile, partner=self)
        ).update(
            is_active=False,
            is_emergency=False,
            heartbeat_alert_sent=False,
        )
        return True

    @classmethod
    def link_by_invite_code(cls, profile, invite_code):
        """Resolve invite code and link profiles. Returns (ok, message)."""
        code = (invite_code or '').strip().lower()
        if not code:
            return False, "Invalid invite code."
        try:
            partner = cls.objects.get(invite_code=code)
        except cls.DoesNotExist:
            return False, "Invalid invite code."
        return profile.link_with(partner)

    def __str__(self):
        partners = self.get_partners()
        return f"{self.user.email} - Partners: {', '.join(p.user.email for p in partners) or 'None'}"

    def is_missing(self):
        return timezone.now() - self.last_check_in > timezone.timedelta(
            hours=self.danger_hours
        )

    def is_warning(self):
        delta = timezone.now() - self.last_check_in
        return (
            timezone.timedelta(hours=self.warning_hours)
            < delta
            <= timezone.timedelta(hours=self.danger_hours)
        )

    @property
    def danger_hours(self):
        """Use the shortest active connection window for this user's timer."""
        relation_levels = UserPartnerMappings.objects.filter(
            user=self,
            is_active=True,
        ).values_list('relation_level', flat=True)
        return min(
            (
                UserPartnerMappings.danger_hours_for_level(level)
                for level in relation_levels
            ),
            default=48,
        )

    @property
    def warning_hours(self):
        return self.danger_hours / 2

class UserPartnerMappings(models.Model):
    class RelationLevel(models.IntegerChoices):
        VERY_STRONG = 1, 'Very strong'
        STRONG = 2, 'Strong'
        CLOSE = 3, 'Close'
        REGULAR = 4, 'Regular'
        CASUAL = 5, 'Casual'

    RELATION_DANGER_HOURS = {
        RelationLevel.VERY_STRONG: 12,
        RelationLevel.STRONG: 18,
        RelationLevel.CLOSE: 24,
        RelationLevel.REGULAR: 36,
        RelationLevel.CASUAL: 48,
    }

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='mappings_as_user')
    partner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='mappings_as_partner')
    is_active = models.BooleanField(default=True)
    is_emergency = models.BooleanField(default=False)
    relation_level = models.PositiveSmallIntegerField(
        choices=RelationLevel.choices,
        default=RelationLevel.CASUAL,
    )
    heartbeat_alert_sent = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'partner'],
                name='unique_user_partner_mapping',
            ),
        ]

    def __str__(self):
        return f"{self.user.user.email} <-> {self.partner.user.email}"

    @classmethod
    def danger_hours_for_level(cls, level):
        try:
            relation_level = cls.RelationLevel(int(level))
        except (TypeError, ValueError):
            relation_level = cls.RelationLevel.CASUAL
        return cls.RELATION_DANGER_HOURS[relation_level]

    @property
    def danger_hours(self):
        return self.danger_hours_for_level(self.relation_level)

    @property
    def warning_hours(self):
        return self.danger_hours / 2

    @property
    def relation_label(self):
        return self.get_relation_level_display()

    def is_missing(self):
        return (
            timezone.now() - self.partner.last_check_in
            > timezone.timedelta(hours=self.danger_hours)
        )

    def is_warning(self):
        delta = timezone.now() - self.partner.last_check_in
        return (
            timezone.timedelta(hours=self.warning_hours)
            < delta
            <= timezone.timedelta(hours=self.danger_hours)
        )


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
