# LINE Notification API Documentation

## Overview

LINE Notification API allows the trading bot to send real-time notifications to users via LINE Messaging API. Users must have connected their LINE account via LINE Login before they can receive notifications.

## Prerequisites

1. **LINE Channel Access Token**: Set `LINE_CHANNEL_ACCESS_TOKEN` in environment variables
2. **User LINE Connection**: User must have connected LINE account (check via `UserProfile.is_line_connected()`)
3. **Bot API Key**: All endpoints require valid Bot API Key in header

## Authentication

All endpoints require Bot API Key authentication:

```
X-BOT-API-KEY: your-bot-api-key-here
```

## Base URL

```
/api/notify/
```

---

## Endpoints

### 1. Send Trade Notification

Send notification when a trade is opened or closed.

**Endpoint:** `POST /api/notify/trade/`

**Request Body:**

```json
{
  "mt5_account_id": "12345678",
  "notification_type": "trade_opened",
  "trade_data": {
    "symbol": "EURUSD",
    "position_type": "BUY",
    "entry_price": "1.0850",
    "lot_size": "0.10"
  }
}
```

**For Trade Closed:**

```json
{
  "mt5_account_id": "12345678",
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
```

**Fields:**

- `mt5_account_id` (string, required): MT5 account ID
- `notification_type` (string, required): Either "trade_opened" or "trade_closed"
- `trade_data` (object, required): Trade details
  - `symbol` (string): Trading symbol (e.g., "EURUSD")
  - `position_type` (string): "BUY" or "SELL"
  - `entry_price` (string): Entry price
  - `exit_price` (string): Exit price (for trade_closed only)
  - `lot_size` (string): Lot size
  - `profit_loss` (string): Profit/loss amount (for trade_closed only)
  - `close_reason` (string): Close reason like "TP", "SL", "Manual" (for trade_closed only)

**Response (Success):**

```json
{
  "status": "success",
  "message": "Notification sent successfully",
  "notification_sent": true
}
```

**Response (LINE Not Connected):**

```json
{
  "status": "success",
  "message": "User has not connected LINE account, notification skipped",
  "notification_sent": false
}
```

**Response (Error):**

```json
{
  "status": "error",
  "message": "Failed to send notification",
  "error": "Error details",
  "notification_sent": false
}
```

---

### 2. Send Bot Status Notification

Send notification when bot status changes (ACTIVE, PAUSED, DOWN, ERROR).

**Endpoint:** `POST /api/notify/bot-status/`

**Request Body:**

```json
{
  "mt5_account_id": "12345678",
  "status": "PAUSED",
  "reason": "Daily drawdown limit reached"
}
```

**Fields:**

- `mt5_account_id` (string, required): MT5 account ID
- `status` (string, required): Bot status - "ACTIVE", "PAUSED", "DOWN", or "ERROR"
- `reason` (string, optional): Reason for status change

**Response:** Same as trade notification endpoint

---

### 3. Send Daily Summary Notification

Send daily trading summary to user.

**Endpoint:** `POST /api/notify/daily-summary/`

**Request Body:**

```json
{
  "mt5_account_id": "12345678",
  "summary_data": {
    "total_trades": 5,
    "profit_loss": 125.50,
    "win_rate": 60.0
  }
}
```

**Fields:**

- `mt5_account_id` (string, required): MT5 account ID
- `summary_data` (object, required): Daily summary data
  - `total_trades` (number): Total number of trades today
  - `profit_loss` (number): Total profit/loss for the day
  - `win_rate` (number): Win rate percentage (0-100)

**Response:** Same as trade notification endpoint

---

### 4. Send Account Alert Notification

Send account alerts (e.g., low balance, high drawdown, margin warning).

**Endpoint:** `POST /api/notify/account-alert/`

**Request Body:**

```json
{
  "mt5_account_id": "12345678",
  "alert_type": "Low Balance",
  "message": "Your account balance is below $100"
}
```

**Fields:**

- `mt5_account_id` (string, required): MT5 account ID
- `alert_type` (string, required): Type of alert (e.g., "Low Balance", "High Drawdown", "Margin Warning")
- `message` (string, required): Alert message to send to user

**Response:** Same as trade notification endpoint

---

## Error Codes

- `400`: Bad Request - Invalid JSON or missing required fields
- `404`: Not Found - Trade account not found or user profile not found
- `500`: Internal Server Error - Failed to send LINE notification

---

## Example Usage (Python)

```python
import requests
import json

# Configuration
API_URL = "https://your-domain.com/api/notify/trade/"
BOT_API_KEY = "your-bot-api-key"

# Prepare notification data
data = {
    "mt5_account_id": "12345678",
    "notification_type": "trade_opened",
    "trade_data": {
        "symbol": "EURUSD",
        "position_type": "BUY",
        "entry_price": "1.0850",
        "lot_size": "0.10"
    }
}

# Send notification
headers = {
    "X-BOT-API-KEY": BOT_API_KEY,
    "Content-Type": "application/json"
}

response = requests.post(API_URL, headers=headers, json=data)
result = response.json()

print(f"Status: {result['status']}")
print(f"Notification sent: {result.get('notification_sent', False)}")
```

---

## Setup Instructions

### 1. LINE Messaging API Setup

1. Go to [LINE Developers Console](https://developers.line.biz/)
2. Create a new Messaging API channel (or use existing channel)
3. Go to "Messaging API" tab
4. Copy the **Channel Access Token**

### 2. Environment Variables

Add to your `.env` file:

```bash
# LINE Login (already configured)
LINE_CHANNEL_ID=your-channel-id
LINE_CHANNEL_SECRET=your-channel-secret
LINE_CALLBACK_URL=https://your-domain.com/auth/line/callback/

# LINE Messaging API (for notifications)
LINE_CHANNEL_ACCESS_TOKEN=your-channel-access-token
```

### 3. Enable Messaging API Features

In LINE Developers Console:

1. Go to "Messaging API" tab
2. Enable "Use webhooks" (optional, if you want to receive messages from users)
3. Disable "Auto-reply messages" and "Greeting messages" (to avoid conflicting with your bot)

---

## Notes

- Notifications will only be sent if user has connected their LINE account via LINE Login
- If user has not connected LINE, the API will return success but with `notification_sent: false`
- The system uses the same LINE channel for both Login and Messaging API
- Make sure your LINE channel has "Messaging API" enabled
- Rate limits apply according to LINE Messaging API restrictions

---

## Notification Message Formats

### Trade Opened
```
🔔 เทรดใหม่เปิด!

📊 บัญชี: My Trading Account
💱 คู่เงิน: EURUSD
📈 ประเภท: BUY
💰 ราคาเข้า: 1.0850
📦 Lot Size: 0.10

ดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor
```

### Trade Closed
```
🔔 เทรดปิด!

📊 บัญชี: My Trading Account
💱 คู่เงิน: EURUSD
✅ กำไร/ขาดทุน: +$10.50
🏁 สาเหตุ: TP

ดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor
```

### Bot Status Change
```
⏸️ สถานะ Bot เปลี่ยน!

📊 บัญชี: My Trading Account
📡 สถานะ: PAUSED
💬 เหตุผล: Daily drawdown limit reached

ดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor
```

### Daily Summary
```
📊 สรุปผลวันนี้

📈 บัญชี: My Trading Account
🔢 จำนวนเทรด: 5
✅ กำไร/ขาดทุน: +$125.50
🎯 Win Rate: 60.0%

ดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor
```

### Account Alert
```
⚠️ แจ้งเตือนบัญชี!

📊 บัญชี: My Trading Account
🔔 ประเภท: Low Balance
💬 Your account balance is below $100

ดูรายละเอียดเพิ่มเติมได้ที่แอป FX Bot Monitor
```
