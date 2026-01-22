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

    def get_partner(self):
        mappings = UserPartnerMappings.objects.filter(
            (Q(user=self) | Q(partner=self)) & Q(is_active=True)
        )
        if mappings.exists():
            mapping = mappings.first()
            return mapping.partner if mapping.user == self else mapping.user
        return None

    def __str__(self):
        partner = self.get_partner()
        return f"{self.user.email} - Partner: {partner.user.email if partner else 'None'}"

    def is_missing(self):
        return timezone.now() - self.last_check_in > timezone.timedelta(hours=48)

    def is_warning(self):
        delta = timezone.now() - self.last_check_in
        return timezone.timedelta(hours=32) < delta <= timezone.timedelta(hours=48)

class UserPartnerMappings(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='mappings_as_user')
    partner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='mappings_as_partner')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.user.email} <-> {self.partner.user.email}"
