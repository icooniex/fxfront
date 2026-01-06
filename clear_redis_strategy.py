#!/usr/bin/env python
"""Clear strategy config บน Redis"""

import redis
from decouple import config

REDIS_URL = config('REDIS_URL')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# หา keys ทั้งหมด
keys = redis_client.keys("bot:strategy_config:*")

if not keys:
    print("ไม่มีข้อมูลให้ลบ")
else:
    print(f"\n🗑️  กำลังลบ {len(keys)} keys...\n")
    for key in keys:
        redis_client.delete(key)
        print(f"   ✅ ลบ {key}")
    print(f"\n✅ ลบเสร็จแล้ว ({len(keys)} keys)")

redis_client.close()
