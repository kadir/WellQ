# Generated manually for PlatformSettings model

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_role_userprofile'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformSettings',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('epss_url', models.URLField(default='https://epss.empiricalsecurity.com/epss_scores-current.csv.gz', help_text='URL for EPSS scores CSV (gzipped)')),
                ('kev_url', models.URLField(default='https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json', help_text='URL for CISA KEV JSON feed')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Platform Settings',
                'verbose_name_plural': 'Platform Settings',
            },
        ),
    ]




