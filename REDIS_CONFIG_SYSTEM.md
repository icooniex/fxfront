# Redis-Based Configuration System

## Overview

The system uses Redis as a high-performance cache layer for real-time communication between the Django server and MT5 trading bots. This enables efficient configuration updates, heartbeat monitoring, and status synchronization.

## Architecture

### Flow Diagram

```
Bot → Redis (heartbeat) ← Server (status updates)
Bot ← Redis (version check) → Server (config updates)
Bot → API (fetch config) ← Server (on version change)
```

## Redis Keys Structure

### 1. Bot Heartbeat (Bot → Redis)
**Key**: `bot:heartbeat:{mt5_account_id}`  
**Type**: Hash  
**TTL**: 60 seconds  
**Fields**:
- `mt5_account_id`: Account identifier
- `timestamp`: ISO 8601 timestamp
- `bot_status`: Current bot status (ACTIVE/PAUSED/DOWN)
- `current_balance`: Current account balance
- `peak_balance`: Peak balance for DD calculation
- `dd_blocked`: Whether bot is blocked by DD protection
- `dd_block_reason`: Reason for DD block (if applicable)
- `last_seen`: Last heartbeat timestamp

### 2. Server Heartbeat (Server → Redis)
**Key**: `server:heartbeat:{mt5_account_id}`  
**Type**: Hash  
**TTL**: 300 seconds (5 minutes)  
**Fields**:
- `bot_status`: Server-side bot status (ACTIVE/PAUSED)
- `account_status`: Account status (ACTIVE/INACTIVE)
- `subscription_status`: Subscription status (ACTIVE/EXPIRED/CANCELLED)
- `dd_blocked`: DD protection status
- `dd_block_reason`: DD block reason (if applicable)
- `last_update`: Server update timestamp

### 3. Trade Config Version (Server → Redis)
**Key**: `bot:trade_config:{mt5_account_id}`  
**Type**: Hash  
**TTL**: 24 hours  
**Fields**:
- `version`: Integer version number (increments on config change)

### 4. Strategy Config Version (Server → Redis)
**Key**: `bot:strategy_config:{mt5_account_id}:{strategy_id}`  
**Type**: Hash  
**TTL**: 24 hours  
**Fields**:
- `version`: Integer version number (increments on parameter change)

## Bot Flow

### 1. Heartbeat & Status Check Loop

```python
# Every 30 seconds
1. send_heartbeat_redis(mt5_account_id, bot_status, balance, peak_balance, dd_blocked)
2. server_status = get_server_heartbeat_from_redis(mt5_account_id)
3. if server_status['bot_status'] == 'PAUSED':
       pause_bot()
4. if server_status['subscription_status'] != 'ACTIVE':
       pause_bot()
```

### 2. Trade Config Update Check

```python
# Every 60 seconds or before trading
1. current_version = get_trade_config_version_from_redis(mt5_account_id)
2. if current_version != local_version:
       config = fetch_trade_config_from_api(mt5_account_id)
       update_local_config(config)
       local_version = current_version
```

### 3. Strategy Config Update Check

```python
# Every 60 seconds or before strategy execution
for strategy in active_strategies:
    1. current_version = get_strategy_config_version_from_redis(mt5_account_id, strategy.id)
    2. if current_version != strategy.local_version:
           config = fetch_strategy_config_from_api(mt5_account_id, strategy.id)
           strategy.update_parameters(config['parameters_by_symbol'])
           strategy.local_version = current_version
```

## API Endpoints

### 1. Get Trade Config
**Endpoint**: `GET /api/bot/trade-config/{mt5_account_id}/`  
**Auth**: Bot API Key required  
**Returns**:
```json
{
  "status": "success",
  "version": 5,
  "bot_status": "ACTIVE",
  "account_status": "ACTIVE",
  "subscription_status": "ACTIVE",
  "subscription_expiry": "2025-01-25T00:00:00Z",
  "current_balance": "10000.0000",
  "peak_balance": "12000.0000",
  "dd_blocked": false,
  "dd_block_reason": null,
  "risk_config": {
    "dd_protection_enabled": true,
    "daily_dd_limit_percent": 5.0,
    "max_account_dd_percent": 10.0
  },
  "trade_config": {
    "enabled_symbols": ["XAUUSD", "EURUSD"],
    "lot_size": 0.01,
    "auto_pause_on_news": true,
    "dynamic_position_sizing_enabled": false
  },
  "active_bot_id": 1,
  "active_bot_name": "Trend Following Bot"
}
```

### 2. Get Strategy Config
**Endpoint**: `GET /api/bot/strategy-config/{mt5_account_id}/{strategy_id}/`  
**Auth**: Bot API Key required  
**Returns**:
```json
{
  "status": "success",
  "version": 3,
  "bot_strategy_id": 1,
  "bot_strategy_name": "Trend Following Bot",
  "bot_status": "ACTIVE",
  "bot_strategy_class": "TrendFollowingBot",
  "is_pair_trading": false,
  "allowed_symbols": ["XAUUSD", "EURUSD", "GBPUSD"],
  "parameters_by_symbol": {
    "XAUUSD": {
      "threshold_points": 50,
      "stop_loss": 100,
      "take_profit": 200,
      "lookback_period": 100
    },
    "EURUSD": {
      "threshold_points": 20,
      "stop_loss": 30,
      "take_profit": 60,
      "lookback_period": 100
    }
  },
  "optimization_config": {
    "lookback_days": 90,
    "threshold_points_range": [10, 100],
    "tp_sl_ranges": [[20, 200], [40, 400]]
  },
  "last_optimization_date": "2025-12-20T10:30:00Z"
}
```

## Automatic Version Incrementing

The system automatically increments config versions when changes are detected via Django signals:

### Trade Config Version Increments When:
- `trade_config` field changes
- `bot_status` changes (ACTIVE ↔ PAUSED)
- `subscription_status` changes
- `dd_blocked` status changes
- `active_bot` changes

### Strategy Config Version Increments When:
- `current_parameters` changes
- `status` changes
- `allowed_symbols` changes

**Implementation**: See `trading/signals.py` - `handle_trade_account_update()` and `handle_bot_strategy_update()`

## Redis Helper Functions

Located in `trading/api/views.py`:

### Server-Side Functions
```python
# Update server heartbeat for bot to read
update_server_heartbeat_in_redis(trade_account)

# Increment trade config version
update_trade_config_version_in_redis(mt5_account_id, version=None)

# Increment strategy config version
update_strategy_config_version_in_redis(mt5_account_id, strategy_id, version=None)
```

### Bot-Side Functions (for bot client)
```python
# Send bot heartbeat to Redis
send_heartbeat_redis(mt5_account_id, bot_status, balance, peak_balance, dd_blocked, dd_block_reason)

# Read server heartbeat from Redis
get_server_heartbeat_from_redis(mt5_account_id)

# Check trade config version
get_trade_config_version_from_redis(mt5_account_id)

# Check strategy config version
get_strategy_config_version_from_redis(mt5_account_id, strategy_id)

# Fetch full config from API
fetch_trade_config_from_api(mt5_account_id)
fetch_strategy_config_from_api(mt5_account_id, strategy_id)
```

## Setup

### 1. Install Redis Package
```bash
pip install redis==5.0.1
```

### 2. Configure Environment Variable
Add to `.env` or Railway environment variables:
```bash
REDIS_URL=redis://localhost:6379/0  # Local development
# or
REDIS_URL=redis://:password@host:port/0  # Production (Railway, etc)
```

### 3. Redis Service
For local development:
```bash
# macOS with Homebrew
brew install redis
brew services start redis

# Or with Docker
docker run -d -p 6379:6379 redis:7-alpine
```

For production (Railway):
- Add Redis plugin from Railway marketplace
- Railway will automatically set `REDIS_URL` environment variable

## Benefits

1. **Real-time Updates**: Config changes propagate to bots within seconds
2. **Efficient**: Only fetch full config when version changes
3. **Scalable**: Supports multiple bots without database overload
4. **Reliable**: TTL ensures stale data is automatically cleaned
5. **Observable**: Easy to monitor bot health via heartbeat timestamps

## Monitoring

Check bot health in Redis:
```bash
# Check if bot is alive
redis-cli HGETALL bot:heartbeat:123456

# Check server status
redis-cli HGETALL server:heartbeat:123456

# Check config versions
redis-cli HGET bot:trade_config:123456 version
redis-cli HGET bot:strategy_config:123456:1 version
```

## Error Handling

- Redis unavailable → System falls back gracefully (warns in logs)
- API fetch fails → Bot retries with exponential backoff
- Version mismatch → Bot automatically fetches latest config
- Heartbeat expires → Server marks bot as DOWN (after 60s)

## Future Enhancements

- [ ] Redis Pub/Sub for instant config push notifications
- [ ] Centralized bot command system (pause all, emergency stop)
- [ ] Real-time bot metrics aggregation
- [ ] Distributed bot coordination for pair trading
