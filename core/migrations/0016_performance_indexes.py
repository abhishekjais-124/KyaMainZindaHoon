from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_connection_relation_meter'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='userpartnermappings',
            index=models.Index(
                fields=['user', 'is_active'],
                name='core_mapping_user_active_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='userpartnermappings',
            index=models.Index(
                fields=['user', 'is_active', 'is_emergency'],
                name='core_mapping_emergency_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='sosalert',
            index=models.Index(
                fields=['from_user', 'status'],
                name='core_sos_from_status_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='sosalert',
            index=models.Index(
                fields=['to_user', 'status'],
                name='core_sos_to_status_idx',
            ),
        ),
    ]
