from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0003_generate_invite_codes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='invite_code',
            field=models.CharField(max_length=5, unique=True, null=False, blank=False, editable=False),
        ),
    ]
