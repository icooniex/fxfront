#!/usr/bin/env python
"""ดูข้อมูล strategy config บน Redis"""

import redis
from decouple import config

REDIS_URL = config('REDIS_URL')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

print("\n🔍 ข้อมูล Strategy Config บน Redis:\n")

# หา keys ทั้งหมด
keys = redis_client.keys("bot:strategy_config:*")

if not keys:
    print("   ไม่มีข้อมูล")
else:
    for key in sorted(keys):
        print(f"\n📌 {key}")
        data = redis_client.hgetall(key)
        for field, value in data.items():
            print(f"   {field}: {value}")
        ttl = redis_client.ttl(key)
        if ttl > 0:
            print(f"   ⏰ TTL: {ttl//3600} ชม. {(ttl%3600)//60} นาที")

redis_client.close()
