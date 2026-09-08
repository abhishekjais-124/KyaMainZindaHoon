from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_performance_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='auto_checkin_on_warning_danger',
            field=models.BooleanField(default=False),
        ),
    ]
