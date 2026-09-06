from django.db import migrations, models


def preserve_sent_heartbeat_alerts(apps, schema_editor):
    Profile = apps.get_model('core', 'Profile')
    UserPartnerMappings = apps.get_model('core', 'UserPartnerMappings')
    alerted_profile_ids = Profile.objects.filter(
        alert_sent=True,
    ).values_list('id', flat=True)
    UserPartnerMappings.objects.filter(
        user_id__in=alerted_profile_ids,
    ).update(heartbeat_alert_sent=True)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_unique_user_partner_mapping'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpartnermappings',
            name='heartbeat_alert_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userpartnermappings',
            name='relation_level',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, 'Very strong'),
                    (2, 'Strong'),
                    (3, 'Close'),
                    (4, 'Regular'),
                    (5, 'Casual'),
                ],
                default=5,
            ),
        ),
        migrations.RunPython(
            preserve_sent_heartbeat_alerts,
            migrations.RunPython.noop,
        ),
    ]
