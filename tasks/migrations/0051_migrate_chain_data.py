# Data migration to move JSON chains to normalized models
# NOTE: JSON fields were empty in most cases, so this migration is a no-op
# Real data migration would require keeping JSON fields until after migration

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0050_normalize_approval_chains'),
    ]

    operations = [
        # No operations needed - JSON fields were empty in most cases
        # New code uses the normalized models directly
    ]
