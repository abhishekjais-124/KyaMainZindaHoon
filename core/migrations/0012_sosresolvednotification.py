# Generated for SOS resolved popup notification to triggerer

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_userpartnermappings_is_emergency'),
    ]

    operations = [
        migrations.CreateModel(
            name='SOSResolvedNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('seen', models.BooleanField(default=False)),
                ('resolved_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sos_resolved_notifications_given', to='core.profile')),
                ('triggerer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sos_resolved_notifications', to='core.profile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
