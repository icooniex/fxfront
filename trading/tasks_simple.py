"""
Simple Celery Tasks for Testing

เริ่มต้นด้วย tasks ง่ายๆ เพื่อทดสอบว่า Celery ทำงานได้
"""

from celery import shared_task
from django.utils import timezone
import time


@shared_task
def hello_world():
    """
    Task ง่ายสุด - แค่ return ข้อความ
    
    Usage:
        from trading.tasks_simple import hello_world
        result = hello_world.delay()
        print(result.get())
    """
    return {
        "message": "Hello from Celery! 🎉",
        "timestamp": timezone.now().isoformat(),
        "status": "success"
    }


@shared_task
def add_numbers(x, y):
    """
    Task ง่ายๆ - บวกเลข 2 ตัว
    
    Usage:
        from trading.tasks_simple import add_numbers
        result = add_numbers.delay(5, 3)
        print(result.get())  # 8
    """
    result = x + y
    return {
        "x": x,
        "y": y,
        "result": result,
        "message": f"{x} + {y} = {result}"
    }


@shared_task
def test_redis_connection():
    """
    ทดสอบว่า Celery เชื่อมต่อ Redis ได้หรือไม่
    
    Usage:
        from trading.tasks_simple import test_redis_connection
        result = test_redis_connection.delay()
        print(result.get())
    """
    from trading.redis_client import redis_client
    
    try:
        # ลอง ping Redis
        is_connected = redis_client.ping()
        
        if is_connected:
            # ลองเขียน-อ่านข้อมูล
            test_key = "celery_test"
            test_value = f"test_{timezone.now().timestamp()}"
            
            redis_client.setex(test_key, 60, test_value)
            retrieved = redis_client.get(test_key)
            
            return {
                "status": "success",
                "redis_connected": True,
                "write_test": "passed",
                "read_test": "passed",
                "test_value": retrieved,
                "message": "✅ Redis connection working!"
            }
        else:
            return {
                "status": "error",
                "redis_connected": False,
                "message": "❌ Cannot ping Redis"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "redis_connected": False,
            "message": f"❌ Redis error: {str(e)}"
        }


@shared_task
def slow_task(seconds=5):
    """
    Task ที่ใช้เวลานานหน่อย - ใช้ทดสอบ async execution
    
    Usage:
        from trading.tasks_simple import slow_task
        result = slow_task.delay(10)
        # ... ทำอย่างอื่นต่อได้ task จะทำงานเบื้องหลัง
        print(result.get())  # รอจนเสร็จ
    """
    time.sleep(seconds)
    return {
        "message": f"Finished after {seconds} seconds ⏱️",
        "seconds": seconds,
        "completed_at": timezone.now().isoformat()
    }


@shared_task
def test_database_access():
    """
    ทดสอบว่า Celery เข้าถึง Database ได้หรือไม่
    
    Usage:
        from trading.tasks_simple import test_database_access
        result = test_database_access.delay()
        print(result.get())
    """
    try:
        from trading.models import UserTradeAccount
        
        # นับจำนวน accounts
        count = UserTradeAccount.objects.count()
        
        return {
            "status": "success",
            "database_connected": True,
            "accounts_count": count,
            "message": f"✅ Database working! Found {count} accounts"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "database_connected": False,
            "message": f"❌ Database error: {str(e)}"
        }
