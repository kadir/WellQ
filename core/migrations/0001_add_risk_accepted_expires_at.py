# Generated migration for adding risk_accepted_expires_at field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # If there are existing migrations, Django will automatically update this
        # when you run makemigrations
    ]

    operations = [
        migrations.AddField(
            model_name='finding',
            name='risk_accepted_expires_at',
            field=models.DateTimeField(blank=True, db_index=True, help_text='Expiration date for risk accepted status. If set, status will revert to OPEN after this date.', null=True),
        ),
        migrations.AddIndex(
            model_name='finding',
            index=models.Index(fields=['status', 'risk_accepted_expires_at'], name='core_findin_status_risk_idx'),
        ),
    ]

