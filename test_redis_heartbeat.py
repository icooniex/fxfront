#!/usr/bin/env python
"""
Test script to read bot heartbeat from Redis
"""
import redis
from decouple import config
from datetime import datetime
import sys

def test_redis_heartbeat():
    """Test reading heartbeat data from Redis"""
    
    # Get Redis URL from environment
    REDIS_URL = config('REDIS_URL', default=None)
    
    if not REDIS_URL:
        print("❌ REDIS_URL not configured in environment")
        sys.exit(1)
    
    print(f"🔗 Connecting to Redis: {REDIS_URL}")
    
    try:
        # Connect to Redis
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        # Test connection
        redis_client.ping()
        print("✅ Redis connection successful\n")
        
        # Get all bot heartbeat keys
        heartbeat_keys = redis_client.keys("bot:heartbeat:*")
        
        if not heartbeat_keys:
            print("⚠️  No bot heartbeat keys found in Redis")
            print("   Make sure bots are running and sending heartbeats")
            return
        
        print(f"📡 Found {len(heartbeat_keys)} bot heartbeat(s):\n")
        print("=" * 80)
        
        # Read each heartbeat
        for key in heartbeat_keys:
            mt5_account_id = key.split(":")[-1]
            print(f"\n🤖 Bot Account: {mt5_account_id}")
            print("-" * 80)
            
            # Check key type first
            key_type = redis_client.type(key)
            print(f"   Key Type: {key_type}")
            
            if key_type != 'hash':
                print(f"   ⚠️  Expected hash type, but got {key_type}")
                print(f"   This key needs to be deleted and recreated by the bot")
                
                # Try to show current value
                try:
                    if key_type == 'string':
                        value = redis_client.get(key)
                        print(f"   Current Value: {value}")
                    elif key_type == 'list':
                        value = redis_client.lrange(key, 0, -1)
                        print(f"   Current Value: {value}")
                    elif key_type == 'set':
                        value = redis_client.smembers(key)
                        print(f"   Current Value: {value}")
                except Exception as e:
                    print(f"   Cannot read value: {e}")
                continue
            
            # Get all heartbeat data
            heartbeat_data = redis_client.hgetall(key)
            
            if not heartbeat_data:
                print("   ⚠️  No data found")
                continue
            
            # Parse and display data
            last_seen = heartbeat_data.get('last_seen', 'N/A')
            bot_status = heartbeat_data.get('bot_status', 'N/A')
            balance = heartbeat_data.get('balance') or heartbeat_data.get('current_balance', 'N/A')
            peak_balance = heartbeat_data.get('peak_balance', 'N/A')
            dd_blocked = heartbeat_data.get('dd_blocked', 'false')
            dd_block_reason = heartbeat_data.get('dd_block_reason', '-')
            
            print(f"   Last Seen:       {last_seen}")
            print(f"   Bot Status:      {bot_status}")
            print(f"   Balance:         {balance}")
            print(f"   Peak Balance:    {peak_balance}")
            print(f"   DD Blocked:      {dd_blocked}")
            print(f"   DD Block Reason: {dd_block_reason}")
            
            # Calculate time since last heartbeat
            if last_seen != 'N/A':
                try:
                    last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                    now = datetime.now(last_seen_dt.tzinfo)
                    time_diff = (now - last_seen_dt).total_seconds()
                    
                    if time_diff < 60:
                        status_emoji = "🟢"
                        status_text = f"ONLINE ({int(time_diff)}s ago)"
                    else:
                        status_emoji = "🔴"
                        status_text = f"OFFLINE ({int(time_diff)}s ago)"
                    
                    print(f"   Connection:      {status_emoji} {status_text}")
                except Exception as e:
                    print(f"   Connection:      ⚠️  Cannot parse timestamp: {e}")
            
            # Show all raw data
            print(f"\n   📋 Raw Data:")
            for field, value in heartbeat_data.items():
                print(f"      {field}: {value}")
        
        print("\n" + "=" * 80)
        print("✅ Test completed successfully")
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧪 Testing Redis Bot Heartbeat")
    print("=" * 80 + "\n")
    test_redis_heartbeat()
    print()
