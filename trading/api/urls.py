from django.urls import path
from . import views

urlpatterns = [
    # Order management
    path('orders/', views.create_update_order, name='api_create_update_order'),
    
    # Account configuration
    path('account/<str:mt5_account_id>/config/', views.get_account_config, name='api_account_config'),
    
    # Bot heartbeat
    path('heartbeat/', views.bot_heartbeat, name='api_bot_heartbeat'),
    
    # Real-time account data (frontend)
    path('account/<int:account_id>/live/', views.get_account_live_data, name='api_account_live_data'),
    path('dashboard/live/', views.get_dashboard_live_data, name='api_dashboard_live_data'),
]
