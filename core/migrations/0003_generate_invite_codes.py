from django.db import migrations
import random

def generate_unique_invite_code(apps, schema_editor):
    Profile = apps.get_model('core', 'Profile')
    used_codes = set(Profile.objects.exclude(invite_code=None).values_list('invite_code', flat=True))
    for profile in Profile.objects.all():
        if not profile.invite_code:
            while True:
                code = f"{random.randint(10000, 99999)}"
                if code not in used_codes:
                    used_codes.add(code)
                    profile.invite_code = code
                    profile.save(update_fields=["invite_code"])
                    break

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_profile_invite_code'),
    ]

    operations = [
        migrations.RunPython(generate_unique_invite_code, reverse_code=migrations.RunPython.noop),
    ]
