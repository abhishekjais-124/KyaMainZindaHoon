# Generated manually for emergency connections

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_sos_alert'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpartnermappings',
            name='is_emergency',
            field=models.BooleanField(default=False),
        ),
    ]
