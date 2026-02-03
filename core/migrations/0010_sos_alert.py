# Generated manually for SOS feature

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_profile_snooze_enabled'),
    ]

    operations = [
        migrations.CreateModel(
            name='SOSAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('active', 'Active'), ('resolved', 'Resolved')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sos_sent', to='core.profile')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sos_resolved', to='core.profile')),
                ('to_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sos_received', to='core.profile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
