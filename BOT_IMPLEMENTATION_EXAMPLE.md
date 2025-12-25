# Bot Implementation Example

This file shows how to use the Redis-based configuration system in your MT5 bot.

## Complete Bot Flow Example

```python
import time
import requests
import redis
from datetime import datetime
import logging

# Configuration
API_BASE_URL = "https://your-server.railway.app/api"
API_KEY = "your-bot-api-key"
MT5_ACCOUNT_ID = "123456"
REDIS_URL = "redis://:password@host:port/0"

# Setup
logger = logging.getLogger(__name__)
redis_client = redis.from_url(REDIS_URL, decode_responses=True)
headers = {"X-Bot-API-Key": API_KEY}

# Local state
local_trade_config_version = 0
local_strategy_versions = {}  # {strategy_id: version}
trade_config = {}
strategy_configs = {}  # {strategy_id: config}


# =============================================================================
# Redis Helper Functions (from user's provided code)
# =============================================================================

def send_heartbeat_redis(mt5_account_id, bot_status=None, balance=None, peak_balance=None, dd_blocked=False, dd_block_reason=None):
    """Send heartbeat to Redis only (does not return config)"""
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    heartbeat_data = {
        "mt5_account_id": str(mt5_account_id),
        "timestamp": timestamp,
        "dd_blocked": "true" if dd_blocked else "false",
        "last_seen": timestamp
    }
    if bot_status is not None:
        heartbeat_data["bot_status"] = bot_status
    if balance is not None:
        heartbeat_data["current_balance"] = str(balance)
    if peak_balance is not None:
        heartbeat_data["peak_balance"] = str(peak_balance)
    if dd_block_reason is not None:
        heartbeat_data["dd_block_reason"] = dd_block_reason
    
    try:
        heartbeat_key = f"bot:heartbeat:{mt5_account_id}"
        redis_client.hset(heartbeat_key, mapping=heartbeat_data)
        redis_client.expire(heartbeat_key, 60)
        logger.info(f"✅ Heartbeat sent to Redis for account {mt5_account_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Redis heartbeat failed: {e}")
        return False


def get_server_heartbeat_from_redis(mt5_account_id):
    """Get server heartbeat/status from Redis"""
    try:
        server_key = f"server:heartbeat:{mt5_account_id}"
        server_data = redis_client.hgetall(server_key)
        
        if not server_data:
            return {}
        
        response = {}
        for key in ["bot_status", "account_status", "subscription_status", "last_update"]:
            if key in server_data:
                response[key] = server_data[key]
        
        logger.info(f"✅ Server heartbeat retrieved from Redis")
        return response
    except Exception as e:
        logger.error(f"❌ Redis get server heartbeat failed: {e}")
        return {}


def get_trade_config_version_from_redis(mt5_account_id):
    """Check trade config version from Redis"""
    try:
        config_key = f"bot:trade_config:{mt5_account_id}"
        version = redis_client.hget(config_key, "version")
        
        if version:
            return int(version)
        return None
    except Exception as e:
        logger.error(f"❌ Redis get trade config version failed: {e}")
        return None


def get_strategy_config_version_from_redis(mt5_account_id, strategy_id):
    """Check strategy config version from Redis"""
    try:
        config_key = f"bot:strategy_config:{mt5_account_id}:{strategy_id}"
        version = redis_client.hget(config_key, "version")
        
        if version:
            return int(version)
        return None
    except Exception as e:
        logger.error(f"❌ Redis get strategy config version failed: {e}")
        return None


def fetch_trade_config_from_api(mt5_account_id, max_retries=3):
    """Fetch trade config from server API"""
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"{API_BASE_URL}/bot/trade-config/{mt5_account_id}/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Trade config fetched from API (version: {data.get('version')})")
                return data
            else:
                logger.warning(f"Fetch trade config failed with status {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"fetch_trade_config attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


def fetch_strategy_config_from_api(mt5_account_id, strategy_id, max_retries=3):
    """Fetch strategy config from server API"""
    for attempt in range(max_retries):
        try:
            response = requests.get(
                f"{API_BASE_URL}/bot/strategy-config/{mt5_account_id}/{strategy_id}/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Strategy config fetched from API (strategy_id: {strategy_id}, version: {data.get('version')})")
                return data
            else:
                logger.warning(f"Fetch strategy config failed with status {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"fetch_strategy_config attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


# =============================================================================
# Bot Logic
# =============================================================================

def check_server_status():
    """Check server status and handle pause/unpause"""
    global bot_paused
    
    server_status = get_server_heartbeat_from_redis(MT5_ACCOUNT_ID)
    
    if not server_status:
        logger.warning("No server heartbeat available")
        return
    
    # Check if server wants to pause bot
    if server_status.get('bot_status') == 'PAUSED':
        if not bot_paused:
            logger.warning("⏸️  Server requested bot pause")
            pause_bot()
            bot_paused = True
    elif server_status.get('bot_status') == 'ACTIVE':
        if bot_paused:
            logger.info("▶️  Server requested bot resume")
            resume_bot()
            bot_paused = False
    
    # Check subscription status
    if server_status.get('subscription_status') != 'ACTIVE':
        logger.error(f"❌ Subscription not active: {server_status.get('subscription_status')}")
        if not bot_paused:
            pause_bot()
            bot_paused = True


def check_and_update_trade_config():
    """Check if trade config version changed and update if needed"""
    global local_trade_config_version, trade_config
    
    redis_version = get_trade_config_version_from_redis(MT5_ACCOUNT_ID)
    
    if redis_version is None:
        logger.warning("No trade config version in Redis")
        return
    
    if redis_version != local_trade_config_version:
        logger.info(f"📥 Trade config version changed: {local_trade_config_version} → {redis_version}")
        
        # Fetch new config from API
        new_config = fetch_trade_config_from_api(MT5_ACCOUNT_ID)
        
        if new_config:
            trade_config = new_config
            local_trade_config_version = redis_version
            
            # Apply config changes
            apply_trade_config(trade_config)
            logger.info(f"✅ Trade config updated to version {redis_version}")


def check_and_update_strategy_config(strategy_id):
    """Check if strategy config version changed and update if needed"""
    global local_strategy_versions, strategy_configs
    
    redis_version = get_strategy_config_version_from_redis(MT5_ACCOUNT_ID, strategy_id)
    
    if redis_version is None:
        logger.warning(f"No strategy config version in Redis for strategy {strategy_id}")
        return
    
    local_version = local_strategy_versions.get(strategy_id, 0)
    
    if redis_version != local_version:
        logger.info(f"📥 Strategy {strategy_id} config version changed: {local_version} → {redis_version}")
        
        # Fetch new config from API
        new_config = fetch_strategy_config_from_api(MT5_ACCOUNT_ID, strategy_id)
        
        if new_config:
            strategy_configs[strategy_id] = new_config
            local_strategy_versions[strategy_id] = redis_version
            
            # Apply strategy config changes
            apply_strategy_config(strategy_id, new_config)
            logger.info(f"✅ Strategy {strategy_id} config updated to version {redis_version}")


def apply_trade_config(config):
    """Apply trade config to bot"""
    logger.info(f"Applying trade config: {config}")
    
    # Update bot settings
    # Example: update lot size, enabled symbols, risk settings, etc.
    # Implement based on your bot's structure
    pass


def apply_strategy_config(strategy_id, config):
    """Apply strategy config to specific strategy"""
    logger.info(f"Applying strategy {strategy_id} config")
    
    # Update strategy parameters
    parameters_by_symbol = config.get('parameters_by_symbol', {})
    
    # Example: update strategy instance with new parameters
    # Implement based on your bot's structure
    pass


def pause_bot():
    """Pause bot trading"""
    logger.warning("⏸️  Bot paused")
    # Implement bot pause logic


def resume_bot():
    """Resume bot trading"""
    logger.info("▶️  Bot resumed")
    # Implement bot resume logic


# =============================================================================
# Main Bot Loop
# =============================================================================

def main():
    global bot_paused
    bot_paused = False
    
    # Get account balance
    balance = get_account_balance()
    peak_balance = balance
    
    # Active strategies (example)
    active_strategies = [1, 2]  # Strategy IDs
    
    # Initial config fetch
    check_and_update_trade_config()
    for strategy_id in active_strategies:
        check_and_update_strategy_config(strategy_id)
    
    last_heartbeat_time = 0
    last_config_check_time = 0
    
    while True:
        try:
            current_time = time.time()
            
            # Send heartbeat every 30 seconds
            if current_time - last_heartbeat_time >= 30:
                balance = get_account_balance()
                peak_balance = max(peak_balance, balance)
                
                send_heartbeat_redis(
                    MT5_ACCOUNT_ID,
                    bot_status="ACTIVE" if not bot_paused else "PAUSED",
                    balance=balance,
                    peak_balance=peak_balance,
                    dd_blocked=False
                )
                
                # Check server status
                check_server_status()
                
                last_heartbeat_time = current_time
            
            # Check config updates every 60 seconds
            if current_time - last_config_check_time >= 60:
                check_and_update_trade_config()
                
                for strategy_id in active_strategies:
                    check_and_update_strategy_config(strategy_id)
                
                last_config_check_time = current_time
            
            # Execute trading logic if not paused
            if not bot_paused:
                # Execute strategy ticks
                for strategy_id in active_strategies:
                    strategy_config = strategy_configs.get(strategy_id)
                    if strategy_config:
                        execute_strategy_tick(strategy_id, strategy_config)
            
            # Sleep for a bit
            time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)


def get_account_balance():
    """Get current account balance from MT5"""
    # Implement based on your MT5 connection
    return 10000.0


def execute_strategy_tick(strategy_id, strategy_config):
    """Execute one tick of strategy logic"""
    # Implement your strategy execution logic
    pass


if __name__ == "__main__":
    main()
```

## Key Points

1. **Heartbeat**: Send every 30 seconds with current balance and status
2. **Server Status**: Check every 30 seconds for pause/unpause commands
3. **Config Updates**: Check versions every 60 seconds
4. **Version Comparison**: Only fetch from API when version changes
5. **Error Handling**: Retry with exponential backoff on API failures
6. **Graceful Degradation**: Continue working if Redis is temporarily unavailable

## Testing

```python
# Test Redis connection
redis_client.ping()

# Test sending heartbeat
send_heartbeat_redis(MT5_ACCOUNT_ID, bot_status="ACTIVE", balance=10000.0)

# Test reading server status
server_status = get_server_heartbeat_from_redis(MT5_ACCOUNT_ID)
print(server_status)

# Test config version check
version = get_trade_config_version_from_redis(MT5_ACCOUNT_ID)
print(f"Trade config version: {version}")

# Test fetching config
config = fetch_trade_config_from_api(MT5_ACCOUNT_ID)
print(config)
```
