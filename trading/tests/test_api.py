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
    BotAPIKey
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
        """Test sending bot heartbeat successfully"""
        heartbeat_data = {
            'mt5_account_id': '12345678',
            'bot_status': 'ACTIVE',
            'current_balance': '10100.50',
            'timestamp': '2025-11-19T10:30:00Z'
        }
        
        response = self.client.post(
            '/api/bot/heartbeat/',
            data=json.dumps(heartbeat_data),
            **self.api_headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('should_continue', data)
        self.assertTrue(data['should_continue'])
        
        # Verify account was updated
        self.trade_account.refresh_from_db()
        self.assertEqual(self.trade_account.bot_status, 'ACTIVE')
        self.assertEqual(self.trade_account.current_balance, Decimal('10100.50'))
        self.assertIsNotNone(self.trade_account.last_sync_datetime)
    
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
