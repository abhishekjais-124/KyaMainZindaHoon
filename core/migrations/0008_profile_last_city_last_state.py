# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_profile_location_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='last_city',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name='profile',
            name='last_state',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
    ]
