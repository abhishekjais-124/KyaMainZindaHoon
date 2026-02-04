# Generated for "Share location to emergency contacts when in SOS" setting

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_sosresolvednotification'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='share_location_in_sos',
            field=models.BooleanField(default=False),
        ),
    ]
