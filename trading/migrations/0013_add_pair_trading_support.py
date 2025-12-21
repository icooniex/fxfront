# Generated migration for pair trading support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0012_add_dynamic_position_sizing'),
    ]

    operations = [
        migrations.AddField(
            model_name='botstrategy',
            name='is_pair_trading',
            field=models.BooleanField(
                default=False,
                help_text='Whether this strategy trades symbol pairs (e.g., EURUSD/GBPUSD)'
            ),
        ),
        migrations.AlterField(
            model_name='botstrategy',
            name='allowed_symbols',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of trading symbols. For single: ['XAUUSD', 'EURUSD']. For pairs: ['EURUSD/GBPUSD', 'AUDUSD/NZDUSD']"
            ),
        ),
        migrations.AlterField(
            model_name='botstrategy',
            name='strategy_type',
            field=models.CharField(
                blank=True,
                help_text='Strategy type (e.g., Trend Following, Mean Reversion, Scalping, Correlation Divergence)',
                max_length=100
            ),
        ),
    ]
