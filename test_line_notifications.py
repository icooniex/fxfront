"""
Test script for LINE Notification API

This script can be used to test LINE notification functionality without running the full bot.
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"  # Change to your server URL
BOT_API_KEY = "your-bot-api-key-here"  # Change to your actual bot API key
MT5_ACCOUNT_ID = "12345678"  # Change to test MT5 account ID

# API Endpoints
ENDPOINTS = {
    "trade": f"{BASE_URL}/api/notify/trade/",
    "bot_status": f"{BASE_URL}/api/notify/bot-status/",
    "daily_summary": f"{BASE_URL}/api/notify/daily-summary/",
    "account_alert": f"{BASE_URL}/api/notify/account-alert/"
}

# Headers
HEADERS = {
    "X-BOT-API-KEY": BOT_API_KEY,
    "Content-Type": "application/json"
}


def test_trade_opened():
    """Test trade opened notification"""
    print("\n📊 Testing Trade Opened Notification...")
    
    data = {
        "mt5_account_id": MT5_ACCOUNT_ID,
        "notification_type": "trade_opened",
        "trade_data": {
            "symbol": "EURUSD",
            "position_type": "BUY",
            "entry_price": "1.0850",
            "lot_size": "0.10"
        }
    }
    
    response = requests.post(ENDPOINTS["trade"], headers=HEADERS, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_trade_closed():
    """Test trade closed notification"""
    print("\n📊 Testing Trade Closed Notification...")
    
    data = {
        "mt5_account_id": MT5_ACCOUNT_ID,
        "notification_type": "trade_closed",
        "trade_data": {
            "symbol": "EURUSD",
            "position_type": "BUY",
            "entry_price": "1.0850",
            "exit_price": "1.0860",
            "lot_size": "0.10",
            "profit_loss": "10.50",
            "close_reason": "TP"
        }
    }
    
    response = requests.post(ENDPOINTS["trade"], headers=HEADERS, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_bot_status():
    """Test bot status notification"""
    print("\n🤖 Testing Bot Status Notification...")
    
    data = {
        "mt5_account_id": MT5_ACCOUNT_ID,
        "status": "PAUSED",
        "reason": "Daily drawdown limit reached"
    }
    
    response = requests.post(ENDPOINTS["bot_status"], headers=HEADERS, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_daily_summary():
    """Test daily summary notification"""
    print("\n📈 Testing Daily Summary Notification...")
    
    data = {
        "mt5_account_id": MT5_ACCOUNT_ID,
        "summary_data": {
            "total_trades": 5,
            "profit_loss": 125.50,
            "win_rate": 60.0
        }
    }
    
    response = requests.post(ENDPOINTS["daily_summary"], headers=HEADERS, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_account_alert():
    """Test account alert notification"""
    print("\n⚠️  Testing Account Alert Notification...")
    
    data = {
        "mt5_account_id": MT5_ACCOUNT_ID,
        "alert_type": "Low Balance",
        "message": "Your account balance is below $100"
    }
    
    response = requests.post(ENDPOINTS["account_alert"], headers=HEADERS, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def run_all_tests():
    """Run all notification tests"""
    print("=" * 60)
    print("LINE Notification API Test Suite")
    print("=" * 60)
    
    tests = [
        ("Trade Opened", test_trade_opened),
        ("Trade Closed", test_trade_closed),
        ("Bot Status", test_bot_status),
        ("Daily Summary", test_daily_summary),
        ("Account Alert", test_account_alert)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    # Check if configuration is set
    if BOT_API_KEY == "your-bot-api-key-here":
        print("❌ Error: Please set BOT_API_KEY in the script")
        sys.exit(1)
    
    if MT5_ACCOUNT_ID == "12345678":
        print("⚠️  Warning: Using default MT5_ACCOUNT_ID, please update for accurate testing")
    
    # Run tests
    success = run_all_tests()
    sys.exit(0 if success else 1)
