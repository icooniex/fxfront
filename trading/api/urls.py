from django.urls import path
from . import views

urlpatterns = [
    # Order management
    path('orders/', views.create_update_order, name='api_create_update_order'),
    path('orders/batch/', views.batch_create_update_orders, name='api_batch_orders'),
    
    # Account configuration
    path('account/<str:mt5_account_id>/config/', views.get_account_config, name='api_account_config'),
    
    # Bot heartbeat
    path('heartbeat/', views.bot_heartbeat, name='api_bot_heartbeat'),
    
    # Bot trade and strategy configuration (NEW)
    path('bot/trade-config/<str:mt5_account_id>/', views.get_trade_config, name='api_get_trade_config'),
    path('bot/strategy-config/<str:mt5_account_id>/<int:strategy_id>/', views.get_strategy_config, name='api_get_strategy_config'),
    
    # Real-time account data (frontend)
    path('account/<int:account_id>/live/', views.get_account_live_data, name='api_account_live_data'),
    path('account/<int:account_id>/open-only/', views.get_account_open_positions_only, name='api_account_open_only'),
    path('account/<int:account_id>/history/', views.get_account_closed_positions, name='api_account_history'),
    path('dashboard/live/', views.get_dashboard_live_data, name='api_dashboard_live_data'),
    
    # Bot strategy API (for external backtest system)
    path('bot/strategies/', views.get_bot_strategies, name='api_bot_strategies'),
    path('bot/backtest-result/', views.submit_backtest_result, name='api_submit_backtest_result'),
    path('bot/optimization-result/', views.submit_optimization_result, name='api_submit_optimization_result'),
]

