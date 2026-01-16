# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0016_alter_eventcard_final_approver'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='due_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
