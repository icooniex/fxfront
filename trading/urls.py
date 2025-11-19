from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.welcome_view, name='welcome'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Accounts
    path('accounts/', views.accounts_list_view, name='accounts_list'),
    path('account/<int:account_id>/', views.account_detail_view, name='account_detail'),
    
    # Subscriptions
    path('subscription/packages/', views.subscription_packages_view, name='subscription_packages'),
    path('subscription/payment/', views.payment_view, name='payment'),
    path('subscription/payment/submit/', views.payment_submit_view, name='payment_submit'),
    path('subscription/payment/<int:payment_id>/pending/', views.payment_pending_view, name='payment_pending'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    
    # Trades
    path('trades/history/', views.trades_history_view, name='trades_history'),
]
