# Generated migration for adding bot_strategy_class field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0013_add_pair_trading_support'),
    ]

    operations = [
        migrations.AddField(
            model_name='botstrategy',
            name='bot_strategy_class',
            field=models.CharField(
                blank=True,
                help_text='Bot strategy class name (e.g., TrendFollowingBot, CorrelationDivergenceBot)',
                max_length=100
            ),
        ),
    ]
