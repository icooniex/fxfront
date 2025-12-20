# Generated migration for dynamic position sizing feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0011_add_backtest_analysis_images'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionpackage',
            name='allow_dynamic_position_sizing',
            field=models.BooleanField(default=False, help_text='Allow dynamic position sizing based on risk percentage'),
        ),
    ]
