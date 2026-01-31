# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_remove_profile_partner_userpartnermappings'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='share_location_with_friends',
            field=models.BooleanField(default=False),
        ),
    ]
