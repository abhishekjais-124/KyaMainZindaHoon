# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_profile_share_location_with_friends'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='last_latitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='last_longitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='location_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
