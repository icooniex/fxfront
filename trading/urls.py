from django.urls import path, include
from . import views

urlpatterns = [
    # Authentication
    path('', views.welcome_view, name='welcome'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # LINE Login
    path('auth/line/login/', views.line_login_view, name='line_login'),
    path('auth/line/callback/', views.line_callback_view, name='line_callback'),
    path('auth/line/connect/', views.line_connect_view, name='line_connect'),
    path('auth/line/disconnect/', views.line_disconnect_view, name='line_disconnect'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Admin Dashboard (for staff only)
    path('bo/monitor/', views.admin_dashboard_view, name='admin_dashboard'),
    path('bo/backtests/strategy/<int:strategy_id>/', views.backtest_strategy_dashboard, name='backtest_strategy_dashboard'),
    
    # Accounts
    path('accounts/', views.accounts_list_view, name='accounts_list'),
    path('account/<int:account_id>/', views.account_detail_view, name='account_detail'),
    
    # Subscriptions
    path('subscription/packages/', views.subscription_packages_view, name='subscription_packages'),
    path('subscription/payment/', views.payment_view, name='payment'),
    path('subscription/payment/submit/', views.payment_submit_view, name='payment_submit'),
    path('subscription/payment/<int:payment_id>/pending/', views.payment_pending_view, name='payment_pending'),
    path('subscription/payment/<int:payment_id>/reupload/', views.payment_reupload_view, name='payment_reupload'),
    path('subscription/setup-mt5/<int:payment_id>/', views.setup_mt5_account_view, name='setup_mt5_account'),
    
    # Account MT5 Management
    path('account/<int:account_id>/mt5/edit/', views.account_mt5_edit_view, name='account_mt5_edit'),
    path('account/<int:account_id>/mt5/reset/submit/', views.account_mt5_reset_submit_view, name='account_mt5_reset_submit'),
    
    # Add account from quota
    path('quota/<int:quota_id>/add-account/', views.add_account_from_quota_view, name='add_account_from_quota'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    
    # Referral Program
    path('referral/dashboard/', views.referral_dashboard, name='referral_dashboard'),
    
    # Trades
    path('trades/history/', views.trades_history_view, name='trades_history'),
    
    # Bots
    path('bots/', views.bots_list_view, name='bots_list'),
    path('bots/<int:bot_id>/', views.bot_detail_view, name='bot_detail'),
    path('account/<int:account_id>/bot/activate/', views.account_bot_activate_view, name='account_bot_activate'),
    path('account/<int:account_id>/bot/deactivate/', views.account_bot_deactivate_view, name='account_bot_deactivate'),
    path('account/<int:account_id>/bot/config/', views.account_update_bot_config, name='account_update_bot_config'),
    path('account/<int:account_id>/bot/pause/', views.account_bot_pause_view, name='account_bot_pause'),
    path('account/<int:account_id>/bot/resume/', views.account_bot_resume_view, name='account_bot_resume'),
    
    # Bot API
    path('api/bot/', include('trading.api.urls')),
]
