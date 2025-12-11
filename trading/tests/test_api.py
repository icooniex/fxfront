from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json
import secrets

from trading.models import (
    UserProfile,
    SubscriptionPackage,
    UserTradeAccount,
    TradeTransaction,
    BotAPIKey,
    BotStrategy,
    BacktestResult
)


class BotAPITestCase(TestCase):
    """Test cases for Bot API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Create user profile
        self.profile = UserProfile.objects.create(
            user=self.user,
            line_uuid='U1234567890abcdef',
            first_name='Test',
            last_name='User',
            phone_number='0812345678'
        )
        
        # Create subscription package
        self.package = SubscriptionPackage.objects.create(
            name='Test Package',
            description='Test subscription package',
            duration_days=30,
            price=Decimal('1000.00'),
            features={'items': ['Feature 1', 'Feature 2']}
        )
        
        # Create trade account
        self.trade_account = UserTradeAccount.objects.create(
            user=self.user,
            account_name='Test MT5 Account',
            mt5_account_id='12345678',
            broker_name='Test Broker',
            mt5_server='TestBroker-Demo',
            subscription_package=self.package,
            subscription_start=timezone.now(),
            subscription_expiry=timezone.now() + timedelta(days=30),
            subscription_status='ACTIVE',
            bot_status='ACTIVE',
            current_balance=Decimal('10000.00'),
            trade_config={
                'lot_size': 0.1,
                'timeframes': ['M5', 'M15'],
                'max_daily_trades': 10
            }
        )
        
        # Create Bot API Key
        self.api_key = BotAPIKey.objects.create(
            name='Test Bot Key',
            key=secrets.token_urlsafe(48),
            is_active=True
        )
        
        # Set up client
        self.client = Client()
        self.api_headers = {
            'HTTP_AUTHORIZATION': f'Bearer {self.api_key.key}',
            'content_type': 'application/json'
        }
    
    def test_create_order_success(self):
        """Test creating a new order successfully"""
        order_data = {
            'mt5_account_id': '12345678',
            'mt5_order_id': 987654321,
            'symbol': 'EURUSD',
            'position_type': 'BUY',
            'position_status': 'OPEN',
            'opened_at': '2025-11-19T10:30:00Z',
            'entry_price': '1.0850',
            'lot_size': '0.10',
            'profit_loss': '0.00',
            'commission': '0.50',
            'take_profit': '1.0900',
            'stop_loss': '1.0800'
        }
        
        response = self.client.post(
            '/api/bot/orders/',
            data=json.dumps(order_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'created')
        self.assertEqual(data['order_id'], 987654321)
        
        # Verify order was created in database
        order = TradeTransaction.objects.get(mt5_order_id=987654321)
        self.assertEqual(order.symbol, 'EURUSD')
        self.assertEqual(order.position_type, 'BUY')
        self.assertEqual(order.lot_size, Decimal('0.10'))
    
    def test_update_existing_order(self):
        """Test updating an existing order"""
        # Create initial order
        order = TradeTransaction.objects.create(
            trade_account=self.trade_account,
            mt5_order_id=987654321,
            symbol='EURUSD',
            position_type='BUY',
            position_status='OPEN',
            opened_at=timezone.now(),
            entry_price=Decimal('1.0850'),
            lot_size=Decimal('0.10'),
            profit_loss=Decimal('0.00')
        )
        
        # Update order to closed
        update_data = {
            'mt5_account_id': '12345678',
            'mt5_order_id': 987654321,
            'symbol': 'EURUSD',
            'position_type': 'BUY',
            'position_status': 'CLOSED',
            'opened_at': '2025-11-19T10:30:00Z',
            'closed_at': '2025-11-19T11:30:00Z',
            'entry_price': '1.0850',
            'exit_price': '1.0900',
            'lot_size': '0.10',
            'profit_loss': '50.00',
            'commission': '0.50'
        }
        
        response = self.client.post(
            '/api/bot/orders/',
            data=json.dumps(update_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['action'], 'updated')
        
        # Verify order was updated
        order.refresh_from_db()
        self.assertEqual(order.position_status, 'CLOSED')
        self.assertEqual(order.exit_price, Decimal('1.0900'))
        self.assertEqual(order.profit_loss, Decimal('50.00'))
    
    def test_create_order_missing_fields(self):
        """Test creating order with missing required fields"""
        order_data = {
            'mt5_account_id': '12345678',
            'symbol': 'EURUSD'
            # Missing required fields
        }
        
        response = self.client.post(
            '/api/bot/orders/',
            data=json.dumps(order_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('errors', data)
    
    def test_create_order_invalid_account(self):
        """Test creating order for non-existent account"""
        order_data = {
            'mt5_account_id': '99999999',
            'mt5_order_id': 987654321,
            'symbol': 'EURUSD',
            'position_type': 'BUY',
            'position_status': 'OPEN',
            'opened_at': '2025-11-19T10:30:00Z',
            'entry_price': '1.0850',
            'lot_size': '0.10',
            'profit_loss': '0.00'
        }
        
        response = self.client.post(
            '/api/bot/orders/',
            data=json.dumps(order_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('not found', data['message'])
    
    def test_create_order_invalid_position_type(self):
        """Test creating order with invalid position type"""
        order_data = {
            'mt5_account_id': '12345678',
            'mt5_order_id': 987654321,
            'symbol': 'EURUSD',
            'position_type': 'INVALID',
            'position_status': 'OPEN',
            'opened_at': '2025-11-19T10:30:00Z',
            'entry_price': '1.0850',
            'lot_size': '0.10',
            'profit_loss': '0.00'
        }
        
        response = self.client.post(
            '/api/bot/orders/',
            data=json.dumps(order_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_create_order_invalid_datetime(self):
        """Test creating order with invalid datetime format"""
        order_data = {
            'mt5_account_id': '12345678',
            'mt5_order_id': 987654321,
            'symbol': 'EURUSD',
            'position_type': 'BUY',
            'position_status': 'OPEN',
            'opened_at': 'invalid-datetime',
            'entry_price': '1.0850',
            'lot_size': '0.10',
            'profit_loss': '0.00'
        }
        
        response = self.client.post(
            '/api/bot/orders/',
            data=json.dumps(order_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('datetime', data['message'].lower())
    
    def test_create_order_with_balance_update(self):
        """Test creating order with current_balance update"""
        order_data = {
            'mt5_account_id': '12345678',
            'mt5_order_id': 987654321,
            'symbol': 'EURUSD',
            'position_type': 'BUY',
            'position_status': 'OPEN',
            'opened_at': '2025-11-19T10:30:00Z',
            'entry_price': '1.0850',
            'lot_size': '0.10',
            'profit_loss': '0.00',
            'current_balance': '10050.25'
        }
        
        response = self.client.post(
            '/api/bot/orders/',
            data=json.dumps(order_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verify balance was updated
        self.trade_account.refresh_from_db()
        self.assertEqual(self.trade_account.current_balance, Decimal('10050.25'))
    
    def test_get_account_config_success(self):
        """Test getting account configuration successfully"""
        response = self.client.get(
            '/api/bot/account/12345678/config/',
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        
        account_data = data['data']
        self.assertEqual(account_data['account_id'], '12345678')
        self.assertEqual(account_data['account_name'], 'Test MT5 Account')
        self.assertEqual(account_data['broker_name'], 'Test Broker')
        self.assertEqual(account_data['bot_status'], 'ACTIVE')
        self.assertEqual(account_data['subscription_status'], 'ACTIVE')
        self.assertIn('trade_config', account_data)
        self.assertEqual(account_data['trade_config']['lot_size'], 0.1)
    
    def test_get_account_config_not_found(self):
        """Test getting config for non-existent account"""
        response = self.client.get(
            '/api/bot/account/99999999/config/',
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_get_account_config_days_remaining(self):
        """Test days_remaining calculation in account config"""
        # Set expiry to 10 days from now
        self.trade_account.subscription_expiry = timezone.now() + timedelta(days=10)
        self.trade_account.save()
        
        response = self.client.get(
            '/api/bot/account/12345678/config/',
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        account_data = data['data']
        self.assertGreaterEqual(account_data['days_remaining'], 9)
        self.assertLessEqual(account_data['days_remaining'], 10)
    
    def test_bot_heartbeat_success(self):
        """Test sending bot heartbeat successfully with trade config and strategy parameters"""
        # Create bot strategy
        bot_strategy = BotStrategy.objects.create(
            name='Test Strategy',
            description='Test strategy for heartbeat',
            version='1.0.0',
            strategy_type='GRID',
            status='ACTIVE',
            allowed_symbols=['EURUSD', 'GBPUSD'],
            current_parameters={
                'grid_spacing': 10,
                'take_profit': 20,
                'stop_loss': 50
            }
        )
        
        # Link strategy to account
        self.trade_account.active_bot = bot_strategy
        self.trade_account.save()
        
        heartbeat_data = {
            'mt5_account_id': '12345678',
            'bot_status': 'ACTIVE',
            'current_balance': '10100.50'
        }
        
        response = self.client.post(
            '/api/bot/heartbeat/',
            data=json.dumps(heartbeat_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify basic response
        self.assertEqual(data['status'], 'success')
        self.assertIn('should_continue', data)
        self.assertTrue(data['should_continue'])
        self.assertIn('server_time', data)
        
        # Verify trade_config is included
        self.assertIn('trade_config', data)
        self.assertEqual(data['trade_config']['lot_size'], 0.1)
        self.assertIn('timeframes', data['trade_config'])
        
        # Verify strategy info is included
        self.assertIn('strategy', data)
        self.assertIsNotNone(data['strategy'])
        self.assertEqual(data['strategy']['name'], 'Test Strategy')
        self.assertEqual(data['strategy']['version'], '1.0.0')
        self.assertEqual(data['strategy']['status'], 'ACTIVE')
        self.assertEqual(data['strategy']['strategy_type'], 'GRID')
        
        # Verify strategy parameters are included in strategy object
        self.assertIn('parameters', data['strategy'])
        self.assertIsNotNone(data['strategy']['parameters'])
        self.assertEqual(data['strategy']['parameters']['grid_spacing'], 10)
        self.assertEqual(data['strategy']['parameters']['take_profit'], 20)
        self.assertEqual(data['strategy']['parameters']['stop_loss'], 50)
        
        # Verify account was updated
        self.trade_account.refresh_from_db()
        self.assertEqual(self.trade_account.bot_status, 'ACTIVE')
        self.assertEqual(self.trade_account.current_balance, Decimal('10100.50'))
        self.assertIsNotNone(self.trade_account.last_sync_datetime)
    
    def test_bot_heartbeat_without_strategy(self):
        """Test heartbeat when no strategy is linked to account"""
        heartbeat_data = {
            'mt5_account_id': '12345678',
            'bot_status': 'ACTIVE',
            'current_balance': '10000.00'
        }
        
        response = self.client.post(
            '/api/bot/heartbeat/',
            data=json.dumps(heartbeat_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify trade_config is still included
        self.assertIn('trade_config', data)
        self.assertEqual(data['trade_config']['lot_size'], 0.1)
        
        # Verify strategy field is None when no strategy linked
        self.assertIn('strategy', data)
        self.assertIsNone(data['strategy'])
    
    def test_bot_heartbeat_expired_subscription(self):
        """Test heartbeat with expired subscription"""
        # Set subscription to expired
        self.trade_account.subscription_expiry = timezone.now() - timedelta(days=1)
        self.trade_account.subscription_status = 'EXPIRED'
        self.trade_account.save()
        
        heartbeat_data = {
            'mt5_account_id': '12345678',
            'bot_status': 'ACTIVE'
        }
        
        response = self.client.post(
            '/api/bot/heartbeat/',
            data=json.dumps(heartbeat_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertFalse(data['should_continue'])  # Should not continue
    
    def test_bot_heartbeat_invalid_status(self):
        """Test heartbeat with invalid bot_status"""
        heartbeat_data = {
            'mt5_account_id': '12345678',
            'bot_status': 'INVALID_STATUS'
        }
        
        response = self.client.post(
            '/api/bot/heartbeat/',
            data=json.dumps(heartbeat_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_bot_heartbeat_missing_account_id(self):
        """Test heartbeat without mt5_account_id"""
        heartbeat_data = {
            'bot_status': 'ACTIVE'
        }
        
        response = self.client.post(
            '/api/bot/heartbeat/',
            data=json.dumps(heartbeat_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('required', data['message'].lower())
    
    def test_bot_heartbeat_paused_status(self):
        """Test heartbeat with PAUSED status"""
        heartbeat_data = {
            'mt5_account_id': '12345678',
            'bot_status': 'PAUSED'
        }
        
        response = self.client.post(
            '/api/bot/heartbeat/',
            data=json.dumps(heartbeat_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify status was updated
        self.trade_account.refresh_from_db()
        self.assertEqual(self.trade_account.bot_status, 'PAUSED')
    
    def test_bot_heartbeat_with_paused_strategy(self):
        """Test heartbeat when strategy is paused by user"""
        # Create paused bot strategy
        bot_strategy = BotStrategy.objects.create(
            name='Paused Strategy',
            description='Test paused strategy',
            version='1.0.0',
            strategy_type='GRID',
            status='PAUSED',  # Strategy is paused
            allowed_symbols=['EURUSD'],
            current_parameters={'grid_spacing': 15}
        )
        
        self.trade_account.active_bot = bot_strategy
        self.trade_account.save()
        
        heartbeat_data = {
            'mt5_account_id': '12345678',
            'bot_status': 'ACTIVE'
        }
        
        response = self.client.post(
            '/api/bot/heartbeat/',
            data=json.dumps(heartbeat_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Verify strategy status is PAUSED in response
        self.assertIn('strategy', data)
        self.assertEqual(data['strategy']['status'], 'PAUSED')
        
        # Bot should check this status and stop trading
        self.assertIn('parameters', data['strategy'])
        self.assertIsNotNone(data['strategy']['parameters'])
    
    def test_invalid_api_key(self):
        """Test API call with invalid API key"""
        invalid_headers = {
            'HTTP_AUTHORIZATION': 'Bearer invalid_key_12345',
            'content_type': 'application/json'
        }
        
        response = self.client.get(
            '/api/bot/account/12345678/config/',
            **invalid_headers
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Invalid', data['message'])
    
    def test_missing_api_key(self):
        """Test API call without API key"""
        response = self.client.get(
            '/api/bot/account/12345678/config/',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_inactive_api_key(self):
        """Test API call with inactive API key"""
        # Deactivate API key
        self.api_key.is_active = False
        self.api_key.save()
        
        response = self.client.get(
            '/api/bot/account/12345678/config/',
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_api_key_last_used_update(self):
        """Test that API key last_used is updated on use"""
        old_last_used = self.api_key.last_used
        
        response = self.client.get(
            '/api/bot/account/12345678/config/',
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify last_used was updated
        self.api_key.refresh_from_db()
        self.assertIsNotNone(self.api_key.last_used)
        if old_last_used:
            self.assertGreater(self.api_key.last_used, old_last_used)
    
    def test_invalid_json_body(self):
        """Test API call with invalid JSON"""
        response = self.client.post(
            '/api/bot/orders/',
            data='invalid json {',
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.api_key.key}'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Invalid JSON', data['message'])
    
    def test_multiple_accounts_same_bot(self):
        """Test bot can manage multiple accounts with same API key"""
        # Create second account
        second_account = UserTradeAccount.objects.create(
            user=self.user,
            account_name='Second MT5 Account',
            mt5_account_id='87654321',
            broker_name='Test Broker',
            mt5_server='TestBroker-Demo',
            subscription_package=self.package,
            subscription_start=timezone.now(),
            subscription_expiry=timezone.now() + timedelta(days=30),
            subscription_status='ACTIVE',
            bot_status='ACTIVE',
            current_balance=Decimal('20000.00')
        )
        
        # Get config for first account
        response1 = self.client.get(
            '/api/bot/account/12345678/config/',
            **self.api_headers
        )
        self.assertEqual(response1.status_code, 200)
        
        # Get config for second account
        response2 = self.client.get(
            '/api/bot/account/87654321/config/',
            **self.api_headers
        )
        self.assertEqual(response2.status_code, 200)
        
        # Verify different account data
        data1 = response1.json()['data']
        data2 = response2.json()['data']
        self.assertNotEqual(data1['account_id'], data2['account_id'])
        self.assertNotEqual(data1['current_balance'], data2['current_balance'])
    
    def test_last_sync_datetime_update(self):
        """Test that last_sync_datetime is updated on order creation"""
        old_last_sync = self.trade_account.last_sync_datetime
        
        order_data = {
            'mt5_account_id': '12345678',
            'mt5_order_id': 987654321,
            'symbol': 'EURUSD',
            'position_type': 'BUY',
            'position_status': 'OPEN',
            'opened_at': '2025-11-19T10:30:00Z',
            'entry_price': '1.0850',
            'lot_size': '0.10',
            'profit_loss': '0.00'
        }
        
        response = self.client.post(
            '/api/bot/orders/',
            data=json.dumps(order_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verify last_sync_datetime was updated
        self.trade_account.refresh_from_db()
        self.assertIsNotNone(self.trade_account.last_sync_datetime)
        if old_last_sync:
            self.assertGreater(self.trade_account.last_sync_datetime, old_last_sync)


class BotStrategyAPITestCase(TestCase):
    """Test cases for Bot Strategy API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # Create subscription packages
        self.basic_package = SubscriptionPackage.objects.create(
            name='Basic Package',
            duration_days=30,
            price=Decimal('1000.00')
        )
        
        self.premium_package = SubscriptionPackage.objects.create(
            name='Premium Package',
            duration_days=30,
            price=Decimal('3000.00')
        )
        
        # Create bot strategies
        self.bot1 = BotStrategy.objects.create(
            name='Trend Follower Bot',
            description='A bot that follows market trends',
            status='ACTIVE',
            version='1.0.0',
            strategy_type='Trend Following',
            allowed_symbols=['XAUUSD', 'EURUSD'],
            optimization_config={
                'lookback_days': 90,
                'threshold_points': 10
            },
            current_parameters={
                'ema_period': 20,
                'rsi_period': 14,
                'tp_points': 50,
                'sl_points': 30
            },
            backtest_range_days=90
        )
        self.bot1.allowed_packages.add(self.basic_package, self.premium_package)
        
        self.bot2 = BotStrategy.objects.create(
            name='Scalping Bot',
            description='High frequency scalping strategy',
            status='BETA',
            version='0.9.0',
            strategy_type='Scalping',
            allowed_symbols=['GBPUSD'],
            optimization_config={
                'lookback_days': 30,
                'threshold_points': 5
            },
            backtest_range_days=30
        )
        self.bot2.allowed_packages.add(self.premium_package)
        
        # Create inactive bot (should not appear in API)
        self.inactive_bot = BotStrategy.objects.create(
            name='Inactive Bot',
            status='INACTIVE',
            version='1.0.0',
            is_active=False
        )
        
        # Create backtest results
        self.backtest1 = BacktestResult.objects.create(
            bot_strategy=self.bot1,
            run_date=timezone.now(),
            backtest_start_date='2025-08-01',
            backtest_end_date='2025-10-31',
            total_trades=50,
            winning_trades=35,
            losing_trades=15,
            win_rate=Decimal('70.00'),
            total_profit=Decimal('1500.50'),
            avg_profit_per_trade=Decimal('30.01'),
            best_trade=Decimal('150.00'),
            worst_trade=Decimal('-80.00'),
            max_drawdown=Decimal('200.00'),
            max_drawdown_percent=Decimal('5.50'),
            is_latest=True
        )
        
        # Create Bot API Key
        self.api_key = BotAPIKey.objects.create(
            name='Test Bot Key',
            key=secrets.token_urlsafe(48),
            is_active=True
        )
        
        # Set up client
        self.client = Client()
        self.api_headers = {
            'HTTP_AUTHORIZATION': f'Bearer {self.api_key.key}',
            'content_type': 'application/json'
        }
    
    def test_get_bot_strategies_success(self):
        """Test getting list of active bot strategies"""
        response = self.client.get(
            '/api/bot/bot/strategies/',
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['status'], 'success')
        self.assertIn('strategies', data['data'])
        self.assertEqual(data['data']['count'], 2)  # Only active bots
        
        # Verify bot data
        strategies = data['data']['strategies']
        bot_names = [s['name'] for s in strategies]
        self.assertIn('Trend Follower Bot', bot_names)
        self.assertIn('Scalping Bot', bot_names)
        self.assertNotIn('Inactive Bot', bot_names)
        
        # Verify bot1 details
        bot1_data = next(s for s in strategies if s['name'] == 'Trend Follower Bot')
        self.assertEqual(bot1_data['status'], 'ACTIVE')
        self.assertEqual(bot1_data['version'], '1.0.0')
        self.assertEqual(bot1_data['strategy_type'], 'Trend Following')
        self.assertListEqual(bot1_data['allowed_symbols'], ['XAUUSD', 'EURUSD'])
        self.assertEqual(len(bot1_data['allowed_packages']), 2)
        self.assertDictEqual(bot1_data['optimization_config'], {
            'lookback_days': 90,
            'threshold_points': 10
        })
        self.assertDictEqual(bot1_data['current_parameters'], {
            'ema_period': 20,
            'rsi_period': 14,
            'tp_points': 50,
            'sl_points': 30
        })
        self.assertEqual(bot1_data['backtest_range_days'], 90)
    
    def test_get_bot_strategies_unauthorized(self):
        """Test accessing bot strategies without API key"""
        response = self.client.get('/api/bot/bot/strategies/')
        
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Authorization', data['message'])
    
    def test_submit_backtest_result_success(self):
        """Test submitting backtest result successfully"""
        backtest_data = {
            'bot_strategy_id': self.bot1.id,
            'backtest_start_date': '2025-09-01',
            'backtest_end_date': '2025-11-20',
            'total_trades': 75,
            'winning_trades': 55,
            'losing_trades': 20,
            'win_rate': '73.33',
            'total_profit': '2500.75',
            'avg_profit_per_trade': '33.34',
            'best_trade': '200.00',
            'worst_trade': '-100.00',
            'max_drawdown': '250.00',
            'max_drawdown_percent': '6.00',
            'raw_data': {
                'trades': [],
                'daily_returns': []
            },
            'set_as_latest': 'true'
        }
        
        response = self.client.post(
            '/api/bot/bot/backtest-result/',
            data=json.dumps(backtest_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        
        self.assertEqual(data['status'], 'success')
        self.assertIn('backtest_result_id', data['data'])
        self.assertEqual(data['data']['bot_strategy_id'], self.bot1.id)
        self.assertTrue(data['data']['is_latest'])
        
        # Verify database record
        backtest = BacktestResult.objects.get(id=data['data']['backtest_result_id'])
        self.assertEqual(backtest.bot_strategy, self.bot1)
        self.assertEqual(backtest.total_trades, 75)
        self.assertEqual(backtest.winning_trades, 55)
        self.assertEqual(backtest.win_rate, Decimal('73.33'))
        self.assertTrue(backtest.is_latest)
        
        # Verify old backtest is no longer latest
        self.backtest1.refresh_from_db()
        self.assertFalse(self.backtest1.is_latest)
        
        # Verify bot's last_backtest_date was updated
        self.bot1.refresh_from_db()
        self.assertIsNotNone(self.bot1.last_backtest_date)
    
    def test_submit_backtest_result_missing_fields(self):
        """Test submitting backtest result with missing required fields"""
        backtest_data = {
            'bot_strategy_id': self.bot1.id,
            # Missing backtest_start_date and backtest_end_date
            'total_trades': 50
        }
        
        response = self.client.post(
            '/api/bot/bot/backtest-result/',
            data=json.dumps(backtest_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('errors', data)
    
    def test_submit_backtest_result_invalid_bot_id(self):
        """Test submitting backtest result with non-existent bot"""
        backtest_data = {
            'bot_strategy_id': 99999,
            'backtest_start_date': '2025-09-01',
            'backtest_end_date': '2025-11-20',
            'total_trades': 50
        }
        
        response = self.client.post(
            '/api/bot/bot/backtest-result/',
            data=json.dumps(backtest_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('not found', data['message'])
    
    def test_submit_backtest_result_invalid_date_format(self):
        """Test submitting backtest result with invalid date format"""
        backtest_data = {
            'bot_strategy_id': self.bot1.id,
            'backtest_start_date': '2025/09/01',  # Wrong format
            'backtest_end_date': '2025-11-20',
            'total_trades': 50
        }
        
        response = self.client.post(
            '/api/bot/bot/backtest-result/',
            data=json.dumps(backtest_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('date format', data['message'])
    
    def test_submit_backtest_result_with_raw_data(self):
        """Test submitting backtest result with complex raw data"""
        backtest_data = {
            'bot_strategy_id': self.bot2.id,
            'backtest_start_date': '2025-10-01',
            'backtest_end_date': '2025-11-20',
            'total_trades': 150,
            'winning_trades': 100,
            'losing_trades': 50,
            'win_rate': '66.67',
            'total_profit': '1000.00',
            'avg_profit_per_trade': '6.67',
            'best_trade': '50.00',
            'worst_trade': '-30.00',
            'max_drawdown': '100.00',
            'max_drawdown_percent': '3.00',
            'raw_data': {
                'trades': [
                    {'order_id': 1, 'profit': 10.50},
                    {'order_id': 2, 'profit': -5.00}
                ],
                'daily_returns': [15.5, -3.2, 8.7],
                'equity_curve': [10000, 10015.5, 10012.3, 10021]
            }
        }
        
        response = self.client.post(
            '/api/bot/bot/backtest-result/',
            data=json.dumps(backtest_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 201)
        
        # Verify raw_data was saved correctly
        backtest = BacktestResult.objects.get(
            bot_strategy=self.bot2,
            is_latest=True
        )
        self.assertIn('trades', backtest.raw_data)
        self.assertIn('daily_returns', backtest.raw_data)
        self.assertEqual(len(backtest.raw_data['trades']), 2)
        self.assertEqual(len(backtest.raw_data['equity_curve']), 4)
    
    def test_submit_optimization_result_success(self):
        """Test submitting optimization result successfully"""
        opt_data = {
            'bot_strategy_id': self.bot1.id,
            'optimized_parameters': {
                'ema_period': 25,
                'rsi_period': 12,
                'tp_points': 60,
                'sl_points': 25,
                'max_positions': 3
            }
        }
        
        response = self.client.post(
            '/api/bot/bot/optimization-result/',
            data=json.dumps(opt_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['bot_strategy_id'], self.bot1.id)
        self.assertDictEqual(data['data']['current_parameters'], opt_data['optimized_parameters'])
        
        # Verify database was updated
        self.bot1.refresh_from_db()
        self.assertDictEqual(self.bot1.current_parameters, opt_data['optimized_parameters'])
        self.assertIsNotNone(self.bot1.last_optimization_date)
    
    def test_submit_optimization_result_missing_bot_id(self):
        """Test submitting optimization result without bot_strategy_id"""
        opt_data = {
            'optimized_parameters': {
                'ema_period': 25
            }
        }
        
        response = self.client.post(
            '/api/bot/bot/optimization-result/',
            data=json.dumps(opt_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('bot_strategy_id', data['message'])
    
    def test_submit_optimization_result_missing_parameters(self):
        """Test submitting optimization result without parameters"""
        opt_data = {
            'bot_strategy_id': self.bot1.id
        }
        
        response = self.client.post(
            '/api/bot/bot/optimization-result/',
            data=json.dumps(opt_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('optimized_parameters', data['message'])
    
    def test_submit_optimization_result_invalid_parameters_type(self):
        """Test submitting optimization result with non-dict parameters"""
        opt_data = {
            'bot_strategy_id': self.bot1.id,
            'optimized_parameters': 'not a dict'
        }
        
        response = self.client.post(
            '/api/bot/bot/optimization-result/',
            data=json.dumps(opt_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('JSON object', data['message'])
    
    def test_submit_optimization_result_inactive_bot(self):
        """Test submitting optimization result for inactive bot"""
        opt_data = {
            'bot_strategy_id': self.inactive_bot.id,
            'optimized_parameters': {'test': 'value'}
        }
        
        response = self.client.post(
            '/api/bot/bot/optimization-result/',
            data=json.dumps(opt_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data['status'], 'error')
    
    def test_api_key_last_used_updated(self):
        """Test that API key's last_used timestamp is updated on use"""
        old_last_used = self.api_key.last_used
        
        response = self.client.get(
            '/api/bot/bot/strategies/',
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify last_used was updated
        self.api_key.refresh_from_db()
        self.assertIsNotNone(self.api_key.last_used)
        if old_last_used:
            self.assertGreater(self.api_key.last_used, old_last_used)
    
    def test_multiple_backtest_results_history(self):
        """Test that multiple backtest results can be stored for history"""
        # Create multiple backtest results
        BacktestResult.objects.create(
            bot_strategy=self.bot1,
            run_date=timezone.now() - timedelta(days=14),
            backtest_start_date='2025-07-01',
            backtest_end_date='2025-09-30',
            total_trades=40,
            winning_trades=30,
            losing_trades=10,
            win_rate=Decimal('75.00'),
            total_profit=Decimal('1200.00'),
            avg_profit_per_trade=Decimal('30.00'),
            best_trade=Decimal('120.00'),
            worst_trade=Decimal('-60.00'),
            max_drawdown=Decimal('150.00'),
            max_drawdown_percent=Decimal('4.00'),
            is_latest=False  # Old result
        )
        
        BacktestResult.objects.create(
            bot_strategy=self.bot1,
            run_date=timezone.now() - timedelta(days=7),
            backtest_start_date='2025-08-01',
            backtest_end_date='2025-10-31',
            total_trades=45,
            winning_trades=32,
            losing_trades=13,
            win_rate=Decimal('71.11'),
            total_profit=Decimal('1400.00'),
            avg_profit_per_trade=Decimal('31.11'),
            best_trade=Decimal('130.00'),
            worst_trade=Decimal('-70.00'),
            max_drawdown=Decimal('180.00'),
            max_drawdown_percent=Decimal('4.80'),
            is_latest=False  # Old result
        )
        
        # Verify we have 3 total results for bot1
        total_results = BacktestResult.objects.filter(bot_strategy=self.bot1).count()
        self.assertEqual(total_results, 3)  # Including self.backtest1 from setUp
        
        # Verify only one is marked as latest
        latest_results = BacktestResult.objects.filter(
            bot_strategy=self.bot1,
            is_latest=True
        )
        self.assertEqual(latest_results.count(), 1)
