# Deduplicate soft-deleted friend links, then enforce uniqueness on (user, partner).

from django.db import migrations, models


def dedupe_user_partner_mappings(apps, schema_editor):
    UserPartnerMappings = apps.get_model('core', 'UserPartnerMappings')
    # Prefer active rows, then highest id.
    kept = set()
    qs = UserPartnerMappings.objects.all().order_by(
        'user_id', 'partner_id', '-is_active', '-id'
    )
    for mapping in qs.iterator():
        key = (mapping.user_id, mapping.partner_id)
        if key in kept:
            mapping.delete()
        else:
            kept.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_profile_share_location_in_sos'),
    ]

    operations = [
        migrations.RunPython(dedupe_user_partner_mappings, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='userpartnermappings',
            constraint=models.UniqueConstraint(
                fields=('user', 'partner'),
                name='unique_user_partner_mapping',
            ),
        ),
    ]
