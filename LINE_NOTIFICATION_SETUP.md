# LINE Notification Feature - Quick Start Guide

## 📱 Overview

LINE Notification feature ช่วยให้ระบบ FX Bot Monitor สามารถส่งการแจ้งเตือนแบบ real-time ไปยังผู้ใช้ผ่าน LINE Messaging API

**คุณสมบัติหลัก:**
- ✅ แจ้งเตือนเมื่อมีเทรดเปิดใหม่
- ✅ แจ้งเตือนเมื่อปิดเทรด (พร้อมกำไร/ขาดทุน)
- ✅ แจ้งเตือนเมื่อสถานะ Bot เปลี่ยน
- ✅ สรุปผลเทรดรายวัน
- ✅ แจ้งเตือนบัญชี (ยอดเงินต่ำ, drawdown สูง)

## 🔧 Setup

### 1. ติดตั้ง Dependencies

Library ที่จำเป็นมีอยู่แล้วใน `requirements.txt`:
- `requests` - สำหรับเรียก LINE API
- `django` - Framework หลัก

### 2. ตั้งค่า Environment Variables

เพิ่มใน `.env` file:

```bash
# LINE Login (มีอยู่แล้ว)
LINE_CHANNEL_ID=your-channel-id
LINE_CHANNEL_SECRET=your-channel-secret
LINE_CALLBACK_URL=https://your-domain.com/auth/line/callback/

# LINE Messaging API (ใหม่ - สำหรับส่ง notification)
LINE_CHANNEL_ACCESS_TOKEN=your-channel-access-token
```

### 3. รับ Channel Access Token

1. ไปที่ [LINE Developers Console](https://developers.line.biz/)
2. เข้าไปที่ Provider และ Channel ของคุณ
3. ไปที่แท็บ "Messaging API"
4. คัดลอก **Channel Access Token**
5. ใส่ใน `.env` file

### 4. ตั้งค่า LINE Channel

ใน LINE Developers Console > Messaging API:

1. ✅ Enable "Messaging API"
2. ❌ Disable "Auto-reply messages"
3. ❌ Disable "Greeting messages"
4. ✅ (Optional) Enable "Use webhooks" ถ้าต้องการรับข้อความจาก user

## 📚 API Endpoints

### Base URL
```
https://your-domain.com/api/notify/
```

### Authentication
ทุก API ต้องใช้ Bot API Key:
```
X-BOT-API-KEY: your-bot-api-key
```

### Endpoints สำหรับ Bot

1. **แจ้งเตือนเทรด** - `POST /api/notify/trade/`
2. **แจ้งเตือนสถานะ Bot** - `POST /api/notify/bot-status/`
3. **สรุปผลรายวัน** - `POST /api/notify/daily-summary/`
4. **แจ้งเตือนบัญชี** - `POST /api/notify/account-alert/`

ดูรายละเอียดเพิ่มเติมใน [LINE_NOTIFICATION_API.md](LINE_NOTIFICATION_API.md)

## 🧪 การทดสอบ

### ทดสอบด้วย Script

```bash
# แก้ไข configuration ใน test_line_notifications.py
python test_line_notifications.py
```

### ทดสอบด้วย curl

```bash
curl -X POST https://your-domain.com/api/notify/trade/ \
  -H "X-BOT-API-KEY: your-bot-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "mt5_account_id": "12345678",
    "notification_type": "trade_opened",
    "trade_data": {
      "symbol": "EURUSD",
      "position_type": "BUY",
      "entry_price": "1.0850",
      "lot_size": "0.10"
    }
  }'
```

## 🔐 การทำงาน

### Flow การส่ง Notification

1. **Bot เรียก API** → ส่ง request พร้อม mt5_account_id
2. **ระบบหาบัญชี** → หา UserTradeAccount จาก mt5_account_id
3. **ตรวจสอบ LINE** → เช็คว่า user ได้เชื่อมต่อ LINE แล้วหรือยัง
4. **ส่ง Notification** → ถ้าเชื่อมต่อแล้ว จะส่งผ่าน LINE Messaging API
5. **Return Status** → ส่งผลลัพธ์กลับไปให้ bot

### เงื่อนไขการส่ง

- ✅ User ต้องเชื่อมต่อ LINE account ก่อน (ผ่านหน้า Profile)
- ✅ LINE_CHANNEL_ACCESS_TOKEN ต้องตั้งค่าในระบบ
- ✅ Bot API Key ต้องถูกต้อง

ถ้า user ยังไม่ได้เชื่อมต่อ LINE:
- API จะ return `success: true` แต่ `notification_sent: false`
- ไม่มี error เพื่อไม่ให้ bot หยุดทำงาน

## 📝 ตัวอย่างการใช้งาน

### Python (จาก Bot)

```python
import requests

def notify_trade_opened(mt5_account_id, trade_data):
    url = "https://your-domain.com/api/notify/trade/"
    headers = {
        "X-BOT-API-KEY": "your-bot-api-key",
        "Content-Type": "application/json"
    }
    
    payload = {
        "mt5_account_id": mt5_account_id,
        "notification_type": "trade_opened",
        "trade_data": trade_data
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        result = response.json()
        
        if result.get("notification_sent"):
            print("✅ Notification sent successfully")
        else:
            print("ℹ️ User has not connected LINE")
            
    except Exception as e:
        print(f"❌ Error sending notification: {e}")
        # Don't stop bot execution if notification fails
```

### MQL5 (จาก EA)

```cpp
// ใช้ WebRequest เรียก API
string url = "https://your-domain.com/api/notify/trade/";
string headers = "X-BOT-API-KEY: your-bot-api-key\r\nContent-Type: application/json\r\n";

string payload = StringFormat(
    "{\"mt5_account_id\":\"%s\",\"notification_type\":\"trade_opened\",\"trade_data\":{\"symbol\":\"%s\",\"position_type\":\"%s\",\"entry_price\":\"%.5f\",\"lot_size\":\"%.2f\"}}",
    AccountNumber(),
    Symbol(),
    "BUY",
    1.0850,
    0.10
);

char data[];
char result[];
string result_headers;

ArrayResize(data, StringToCharArray(payload, data, 0, WHOLE_ARRAY, CP_UTF8) - 1);
int res = WebRequest("POST", url, headers, 5000, data, result, result_headers);
```

## 📊 Notification Formats

### เทรดเปิด
```
🔔 เทรดใหม่เปิด!

📊 บัญชี: My Trading Account
💱 คู่เงิน: EURUSD
📈 ประเภท: BUY
💰 ราคาเข้า: 1.0850
📦 Lot Size: 0.10
```

### เทรดปิด
```
🔔 เทรดปิด!

📊 บัญชี: My Trading Account
💱 คู่เงิน: EURUSD
✅ กำไร/ขาดทุน: +$10.50
🏁 สาเหตุ: TP
```

## 🔍 Troubleshooting

### ไม่ได้รับ Notification

1. ✅ ตรวจสอบว่า user เชื่อมต่อ LINE แล้ว (หน้า Profile)
2. ✅ ตรวจสอบ `LINE_CHANNEL_ACCESS_TOKEN` ว่าถูกต้อง
3. ✅ ตรวจสอบ Bot API Key
4. ✅ ดู logs ที่ server (`trading/line_notify.py`)

### Error 401 Unauthorized

- ตรวจสอบ Channel Access Token ใน `.env`
- ตรวจสอบว่า token ไม่หมดอายุ

### Error 404 Not Found

- ตรวจสอบว่า mt5_account_id ถูกต้อง
- ตรวจสอบว่าบัญชีมีอยู่ในระบบ

## 📁 Files Structure

```
trading/
├── line_notify.py              # LINE notification service & helpers
├── api/
│   ├── views.py                # API endpoints (เพิ่ม LINE notification)
│   └── urls.py                 # URL routing (เพิ่ม notify/ endpoints)
├── models.py                   # UserProfile.is_line_connected()
└── views.py                    # LINE login flow (มีอยู่แล้ว)

fxfront/
└── settings.py                 # เพิ่ม LINE_CHANNEL_ACCESS_TOKEN

LINE_NOTIFICATION_API.md        # API documentation
test_line_notifications.py      # Test script
```

## 🚀 Next Steps

1. ✅ Setup LINE Channel Access Token
2. ✅ ทดสอบ API ด้วย test script
3. ✅ แจ้งให้ users เชื่อมต่อ LINE (หน้า Profile)
4. ✅ Integrate กับ Bot code
5. ✅ Monitor logs และ error handling

## 📞 Support

- API Documentation: `LINE_NOTIFICATION_API.md`
- Test Script: `test_line_notifications.py`
- LINE Developers: https://developers.line.biz/
