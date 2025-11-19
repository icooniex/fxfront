# MT5 Bot API Documentation

## Authentication

All API endpoints require a master API key in the Authorization header:

```
Authorization: Bearer <your-api-key>
```

## Endpoints

### 1. Create/Update Order Position

**Endpoint:** `POST /api/bot/orders/`

**Description:** Create a new order or update an existing order for any MT5 account.

**Request Body:**
```json
{
  "mt5_account_id": "12345678",
  "mt5_order_id": 987654321,
  "symbol": "EURUSD",
  "position_type": "BUY",
  "position_status": "OPEN",
  "opened_at": "2025-11-19T10:30:00Z",
  "closed_at": null,
  "entry_price": "1.0850",
  "exit_price": null,
  "take_profit": "1.0900",
  "stop_loss": "1.0800",
  "lot_size": "0.10",
  "profit_loss": "0.00",
  "commission": "0.50",
  "swap_fee": "0.00",
  "account_balance_at_close": null,
  "current_balance": "10000.00"
}
```

**Required Fields:**
- `mt5_account_id` - MT5 account number
- `mt5_order_id` - MT5 order ticket number
- `symbol` - Trading pair (e.g., EURUSD)
- `position_type` - BUY or SELL
- `position_status` - OPEN, CLOSED, or PENDING
- `opened_at` - ISO 8601 datetime
- `entry_price` - Entry price as decimal string
- `lot_size` - Lot size as decimal string

**Optional Fields:**
- `closed_at` - Close datetime (ISO 8601)
- `exit_price` - Exit price
- `take_profit` - TP level
- `stop_loss` - SL level
- `profit_loss` - Current P&L
- `commission` - Commission fees
- `swap_fee` - Swap/rollover fees
- `account_balance_at_close` - Balance when order closed
- `current_balance` - Current account balance

**Response (201 Created / 200 OK):**
```json
{
  "status": "success",
  "message": "Order created successfully",
  "order_id": 987654321,
  "action": "created",
  "account_id": "12345678"
}
```

**Error Responses:**
- `400` - Invalid data / Missing required fields / Invalid format
- `401` - Invalid or missing API key
- `404` - Trade account not found

---

### 2. Get Account Configuration

**Endpoint:** `GET /api/bot/account/<mt5_account_id>/config/`

**Description:** Get account subscription status and trading configuration.

**Path Parameters:**
- `mt5_account_id` - MT5 account number

**Response (200 OK):**
```json
{
  "status": "success",
  "data": {
    "account_id": "12345678",
    "account_name": "My Trading Account",
    "broker_name": "IC Markets",
    "broker_server": "ICMarkets-Demo",
    "bot_status": "ACTIVE",
    "subscription_status": "ACTIVE",
    "subscription_expiry": "2025-12-19T23:59:59Z",
    "days_remaining": 30,
    "trade_config": {
      "lot_size": 0.1,
      "timeframes": ["M5", "M15"],
      "max_daily_trades": 10,
      "notification_enabled": true
    },
    "current_balance": "10000.00",
    "last_sync": "2025-11-19T10:30:00Z"
  }
}
```

**Error Responses:**
- `401` - Invalid or missing API key
- `404` - Trade account not found

---

### 3. Bot Heartbeat

**Endpoint:** `POST /api/bot/heartbeat/`

**Description:** Send heartbeat ping to indicate bot is still running. Should be called every 60 seconds.

**Request Body:**
```json
{
  "mt5_account_id": "12345678",
  "bot_status": "ACTIVE",
  "current_balance": "10050.25",
  "timestamp": "2025-11-19T10:30:00Z",
  "message": "Bot running normally"
}
```

**Required Fields:**
- `mt5_account_id` - MT5 account number

**Optional Fields:**
- `bot_status` - ACTIVE, PAUSED, or DOWN
- `current_balance` - Current account balance
- `timestamp` - Current bot timestamp
- `message` - Optional status message

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Heartbeat received",
  "server_time": "2025-11-19T10:30:05Z",
  "should_continue": true,
  "subscription_status": "ACTIVE",
  "days_remaining": 30
}
```

**Important:** The `should_continue` flag indicates whether the bot should continue trading. If `false`, the subscription has expired or been cancelled.

**Error Responses:**
- `400` - Invalid data / Missing mt5_account_id
- `401` - Invalid or missing API key
- `404` - Trade account not found

---

## Error Response Format

All errors follow this format:

```json
{
  "status": "error",
  "message": "Error description",
  "errors": {
    "field_name": ["Error message"]
  }
}
```

## Rate Limiting

Currently no rate limiting is enforced, but it may be added in the future.

## Best Practices

1. **Heartbeat:** Send heartbeat every 60 seconds to maintain bot status
2. **Order Updates:** Send immediately when position status changes
3. **Balance Updates:** Include current_balance in heartbeat or order updates
4. **Error Handling:** Check `should_continue` flag in heartbeat response
5. **Retry Logic:** Implement exponential backoff for failed requests
6. **Logging:** Log all API requests and responses for debugging

## Example: Python Bot Integration

```python
import requests
import time
from datetime import datetime

API_BASE_URL = "http://your-server.com"
API_KEY = "your-master-api-key"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def send_heartbeat(mt5_account_id, bot_status="ACTIVE", balance=None):
    """Send heartbeat to server"""
    data = {
        "mt5_account_id": mt5_account_id,
        "bot_status": bot_status,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    if balance:
        data["current_balance"] = str(balance)
    
    response = requests.post(
        f"{API_BASE_URL}/api/bot/heartbeat/",
        json=data,
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        return result.get("should_continue", False)
    return False

def create_order(mt5_account_id, order_data):
    """Create or update order"""
    response = requests.post(
        f"{API_BASE_URL}/api/bot/orders/",
        json=order_data,
        headers=headers
    )
    return response.json()

def get_account_config(mt5_account_id):
    """Get account configuration"""
    response = requests.get(
        f"{API_BASE_URL}/api/bot/account/{mt5_account_id}/config/",
        headers=headers
    )
    return response.json()

# Main bot loop
while True:
    should_continue = send_heartbeat("12345678")
    if not should_continue:
        print("Subscription expired. Stopping bot.")
        break
    
    # Your trading logic here...
    
    time.sleep(60)  # Wait 60 seconds before next heartbeat
```

## Security Notes

1. **Keep API Key Secret:** Never commit API key to version control
2. **Use HTTPS:** Always use HTTPS in production
3. **Rotate Keys:** Regenerate API key if compromised
4. **Monitor Usage:** Check admin panel for API key usage
