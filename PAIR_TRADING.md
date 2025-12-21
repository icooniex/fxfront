# Pair Trading Support Documentation

## Overview
ระบบรองรับการเทรดแบบ Pair Trading Strategy เช่น Correlation Divergence ที่เทรดเป็นคู่ symbol เช่น EURUSD/GBPUSD

## Database Changes

### BotStrategy Model
เพิ่มฟิลด์ใหม่:
- **`is_pair_trading`** (Boolean) - ระบุว่า strategy นี้เป็น pair trading หรือไม่
- **`allowed_symbols`** (JSON) - รองรับทั้ง single และ pair format

#### Format ของ allowed_symbols:
```python
# Single Symbol Trading (เดิม)
allowed_symbols = ["EURUSD", "GBPUSD", "XAUUSD"]

# Pair Symbol Trading (ใหม่)
allowed_symbols = ["EURUSD/GBPUSD", "AUDUSD/NZDUSD", "EURJPY/GBPJPY"]
```

### Helper Methods
```python
# ตรวจสอบว่า symbol ถูกต้องตาม format ไหม
strategy.validate_symbol_format("EURUSD/GBPUSD")  # True for pair trading

# แยก pair เป็น symbol แต่ละตัว
symbol1, symbol2 = strategy.parse_symbol_pair("EURUSD/GBPUSD")
# Returns: ("EURUSD", "GBPUSD")

# ดึง unique symbols ทั้งหมดจาก pair
strategy.get_all_unique_symbols()
# For ["EURUSD/GBPUSD", "AUDUSD/NZDUSD"]
# Returns: ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"]
```

## API Changes

### 1. bot_heartbeat (POST /api/bot/heartbeat/)
**Response เพิ่ม:**
```json
{
  "strategy": {
    "id": 1,
    "name": "Correlation Divergence v1",
    "is_pair_trading": true,
    "allowed_symbols": ["EURUSD/GBPUSD", "AUDUSD/NZDUSD"],
    "parameters_by_symbol": {
      "EURUSD/GBPUSD": {
        "correlation_period": 20,
        "divergence_threshold": 2.0,
        "tp": 50,
        "sl": 30
      }
    }
  }
}
```

### 2. get_bot_strategies (GET /api/bot/strategies/)
**Response เพิ่ม:**
```json
{
  "status": "success",
  "data": {
    "strategies": [
      {
        "id": 1,
        "name": "Correlation Divergence",
        "is_pair_trading": true,
        "allowed_symbols": ["EURUSD/GBPUSD"],
        "current_parameters": {...}
      }
    ]
  }
}
```

### 3. submit_backtest_result (POST /api/bot/backtest/submit/)
**ไม่ต้องแก้** - รับผล backtest เป็นตัวเลขเหมือนเดิม

### 4. submit_optimization_result (POST /api/bot/optimization/submit/)
**ไม่ต้องแก้** - รับ parameters เป็น JSON object

#### ตัวอย่าง optimized_parameters สำหรับ pair trading:
```json
{
  "optimized_parameters": {
    "EURUSD/GBPUSD": {
      "correlation_period": 20,
      "divergence_threshold": 2.5,
      "tp": 60,
      "sl": 35,
      "lot_size": 0.01
    },
    "AUDUSD/NZDUSD": {
      "correlation_period": 25,
      "divergence_threshold": 2.2,
      "tp": 55,
      "sl": 30,
      "lot_size": 0.01
    }
  }
}
```

## Admin Interface

### BotStrategy Admin
เพิ่มฟิลด์:
- **is_pair_trading** - Checkbox สำหรับระบุว่าเป็น pair trading
- **allowed_symbols** - แสดง description ว่ารูปแบบ single vs pair

ตัวอย่างการกรอกข้อมูล:

**Single Symbol Strategy:**
```json
{
  "is_pair_trading": false,
  "allowed_symbols": ["EURUSD", "GBPUSD", "XAUUSD"]
}
```

**Pair Symbol Strategy:**
```json
{
  "is_pair_trading": true,
  "allowed_symbols": ["EURUSD/GBPUSD", "AUDUSD/NZDUSD"]
}
```

## Bot Configuration (Frontend)

### Trading Symbol Selection
เมื่อเลือก strategy ที่เป็น pair trading:
- แสดงรายการ symbol pairs จาก `allowed_symbols`
- ผู้ใช้เลือก pair เช่น "EURUSD/GBPUSD"
- เก็บลง `trade_config.trading_symbols` เป็น array of pairs

ตัวอย่าง trade_config:
```json
{
  "trading_symbols": ["EURUSD/GBPUSD", "AUDUSD/NZDUSD"],
  "lot_size": 0.01,
  "max_spread": 3.0
}
```

## Bot Implementation (External Bot)

### 1. รับข้อมูล strategy จาก heartbeat
```python
response = requests.post(f"{API_URL}/bot/heartbeat/", json={
    "mt5_account_id": account_id,
    "bot_status": "ACTIVE"
})

strategy = response.json()['strategy']
is_pair = strategy['is_pair_trading']
allowed_symbols = strategy['allowed_symbols']

# For pair trading: ["EURUSD/GBPUSD", "AUDUSD/NZDUSD"]
```

### 2. จัดการ pair trading logic
```python
if is_pair:
    for pair in trade_config['trading_symbols']:
        # Parse pair
        symbol1, symbol2 = pair.split('/')
        
        # Get parameters for this pair
        params = strategy['parameters_by_symbol'].get(pair, {})
        
        # Calculate correlation
        correlation = calculate_correlation(symbol1, symbol2, params['correlation_period'])
        
        # Check divergence
        if abs(correlation) < params['divergence_threshold']:
            # Execute pair trades
            execute_pair_trade(symbol1, symbol2, params)
```

### 3. ส่งผล trades กลับ
```python
# ส่ง orders ตามปกติ แต่ระบุ symbol ทั้งสองตัวแยก
orders = [
    {
        "mt5_order_id": 123,
        "symbol": "EURUSD",  # Symbol แยก
        "position_type": "BUY",
        "lot_size": 0.01,
        # ... other fields
    },
    {
        "mt5_order_id": 124,
        "symbol": "GBPUSD",  # Symbol คู่
        "position_type": "SELL",
        "lot_size": 0.01,
        # ... other fields
    }
]

requests.post(f"{API_URL}/bot/orders/batch/", json=orders)
```

## Migration

Run migration:
```bash
python manage.py migrate trading 0013_add_pair_trading_support
```

## Testing Checklist

- [ ] Create pair trading strategy in admin
- [ ] Set `is_pair_trading=True` and `allowed_symbols=["EURUSD/GBPUSD"]`
- [ ] Test bot heartbeat API returns `is_pair_trading` field
- [ ] Test get_bot_strategies API includes pair info
- [ ] Submit optimization result with pair-based parameters
- [ ] Submit backtest result (no changes needed)
- [ ] Test frontend bot config symbol selection for pairs

## Example: Creating Correlation Divergence Strategy

```python
# In Django Admin or shell
from trading.models import BotStrategy

strategy = BotStrategy.objects.create(
    name="Correlation Divergence EUR/GBP",
    description="Trades EURUSD/GBPUSD pair based on correlation divergence",
    strategy_type="Correlation Divergence",
    version="1.0.0",
    status="ACTIVE",
    is_pair_trading=True,
    allowed_symbols=["EURUSD/GBPUSD", "EURJPY/GBPJPY"],
    backtest_range_days=90,
    optimization_config={
        "correlation_period_range": [10, 50],
        "divergence_threshold_range": [1.5, 3.0],
        "tp_range": [30, 100],
        "sl_range": [20, 60]
    },
    current_parameters={
        "EURUSD/GBPUSD": {
            "correlation_period": 20,
            "divergence_threshold": 2.5,
            "tp": 60,
            "sl": 35,
            "lot_size": 0.01
        }
    }
)
```

## Notes

1. **Backward Compatibility**: ทุก strategy เดิมจะมี `is_pair_trading=False` โดย default
2. **Validation**: ใช้ `validate_symbol_format()` เพื่อเช็คว่า symbol ถูกต้องตาม type
3. **Parameters Structure**: สำหรับ pair trading, keys ใน `current_parameters` ควรเป็น "SYMBOL1/SYMBOL2"
4. **Trade Recording**: แม้จะเป็น pair trading แต่ orders แต่ละตัวยังถูกบันทึกแยกตาม symbol
