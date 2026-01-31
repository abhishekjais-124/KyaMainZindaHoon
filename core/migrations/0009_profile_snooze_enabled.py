# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_profile_last_city_last_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='snooze_enabled',
            field=models.BooleanField(default=False),
        ),
    ]
